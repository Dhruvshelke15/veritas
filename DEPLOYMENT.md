# Deployment

Backend and frontend deploy separately: the backend (FastAPI + ChromaDB + a TensorFlow classifier) needs a persistent server process, so it goes on **Render**; the frontend is a static Vite build, so it goes on **Vercel**. Vercel/CloudFront-style platforms can't host the backend directly — there's no serverless-function shape that fits a long-running process with a ChromaDB index and (optionally) a TensorFlow classifier.

Deploy the backend first — the frontend build needs its URL.

## 1. Backend on Render

1. Push this repo to GitHub (already done if you're reading this from the repo).
2. In Render: **New → Blueprint**, point it at this repo. It'll pick up [`render.yaml`](render.yaml) at the repo root, which defines a Docker web service built from [`Dockerfile`](Dockerfile).
3. Render will prompt for the two secrets marked `sync: false` in `render.yaml`: **`ANTHROPIC_API_KEY`** (generation) and **`HUGGINGFACE_API_KEY`** (embeddings — free account, generate at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens), default "read" scope is enough).
4. Deploy. Corpus ingestion happens lazily on the first real request (`app/ingestion/bootstrap.py`), not at build time — the very first `/ask` or `/documents` call after a cold start will be a bit slower while it seeds the 5 USCIS/ICE docs; every request after that is fast.
5. Once it's live, note the URL Render gives you (`https://<something>.onrender.com`). Confirm it works: `curl https://<something>.onrender.com/health` should return `{"status":"ok"}`.

**Storage is ephemeral by design**: documents uploaded via `/ingest` at runtime, and the seeded corpus itself, live only as long as that container instance does, and get re-seeded from scratch (fast — it's a hosted-API HTTP call now, not a local model load) on the next deploy or restart. If you outgrow this, Render's paid plans support attaching a persistent disk — mount it at `data/chroma` and `data/uploads`.

**Free-tier RAM (confirmed by real incidents, not hypothetical)**: the first deployed version ran embeddings locally via `sentence-transformers`/PyTorch, and that — resident in the same process as ChromaDB and the Claude client — genuinely OOM'd Render's free instance type on every request; Render's own monitoring flagged it directly. Embeddings now go through HuggingFace's hosted Inference API instead (`HuggingFaceEmbeddingFunction` in `app/ingestion/indexer.py`), which removes PyTorch from the deployed process entirely. `render.yaml` also defaults `VERITAS_CLASSIFIER_ENABLED=false` to skip TensorFlow too, since routing already fails open without a classifier (`app/rag/routing.py`) — you lose the out-of-scope pre-filter and the advice-seeking disclaimer, not the citation-validation refusal backstop that actually keeps answers grounded. If you'd rather keep the classifier, upgrade to a paid instance type with more RAM and set `VERITAS_CLASSIFIER_ENABLED=true`.

**Cold starts**: Render's free web services spin down after inactivity, and the first request after idle also has to seed the corpus (a handful of HTTP calls to HuggingFace). Expect the first request after idle to be noticeably slower than the rest; this is expected, not a bug.

## 2. Frontend on Vercel

1. In Vercel: **New Project**, import this repo, set **Root Directory** to `frontend`.
2. Framework preset should auto-detect Vite. Build command `npm run build`, output directory `dist` (Vercel defaults are already correct).
3. Add an environment variable: **`VITE_API_BASE_URL`** = the Render backend URL from step 1 (e.g. `https://veritas-backend.onrender.com`, no trailing slash). This is read at *build* time (see `frontend/src/api/client.ts`) — changing it later requires a redeploy, not just a restart.
4. Deploy. [`vercel.json`](frontend/vercel.json) handles SPA routing so refreshing on `/upload` or `/eval` doesn't 404.

## 3. Close the loop: CORS

The backend only accepts requests from origins listed in `VERITAS_ALLOWED_ORIGINS` (comma-separated; see `app/config.py`). Once you have the Vercel URL, go back to the Render service's environment variables and set:

```
VERITAS_ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app
```

(Include `http://localhost:5173` too, comma-separated, if you still want local dev to hit the deployed backend.) Redeploy the backend for the change to take effect.

`render.yaml` marks this variable `sync: false`, meaning the dashboard value you set here is authoritative and future blueprint syncs (i.e. every push) won't reset it back to the placeholder in the file. If you ever see a real CORS error again after this has already worked once, check the dashboard value first — it's more likely to have been reset than to be a new bug.

## 4. Verify

Open the Vercel URL and repeat the same three checks from [TESTING.md](TESTING.md)'s browser section: ask a real question and confirm it streams and cites sources, ask an out-of-scope question and confirm it refuses, and check `/upload` and `/eval` load without console errors. A browser CORS error in the console almost always means step 3 wasn't done yet or the backend hasn't redeployed since.

## USCIS watch: local schedule (not cloud)

The USCIS discovery job (`backend/scripts/watch_uscis.py`, see README) originally ran on a GitHub Actions weekly cron. USCIS blocks GitHub Actions' datacenter IPs — every scheduled run 403's — while the same script works fine from a residential IP. So `.github/workflows/uscis-watch.yml` is now manual-trigger-only, and the actual recurring scan runs locally via macOS `launchd` instead, from wherever this repo lives on your Mac.

**Install:**

```bash
cp backend/scripts/com.veritas.uscis-watch.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.veritas.uscis-watch.plist
```

This runs `watch_uscis.py --notify` every Monday at 9:00 AM local time (whenever the Mac is next awake, if it was asleep at that moment — launchd doesn't skip a missed run, it fires at the next wake). On finding new relevant items, it fires a macOS notification and updates `data/watch/seen.json` locally; output logs go to `data/watch/launchd.log` / `launchd.err.log` (gitignored).

**Check it's loaded:** `launchctl list | grep veritas` should show `com.veritas.uscis-watch`.

**Run it once immediately** (don't wait for Monday): `launchctl start com.veritas.uscis-watch`, then check `data/watch/launchd.log`.

**Uninstall:**

```bash
launchctl unload ~/Library/LaunchAgents/com.veritas.uscis-watch.plist
rm ~/Library/LaunchAgents/com.veritas.uscis-watch.plist
```

**Note:** the plist hardcodes this machine's absolute path (`/Users/dhruvshelke/Desktop/veritas/...`). If you move or clone the repo elsewhere, edit the paths in `backend/scripts/com.veritas.uscis-watch.plist` before reinstalling. It also doesn't auto-commit `data/watch/seen.json` back to git — that state file will show as locally modified after a run; commit it whenever convenient, the same way the classifier model or golden set get committed.

## Known gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Browser console: CORS error on every `/api/*` request | `VERITAS_ALLOWED_ORIGINS` on Render doesn't include the Vercel origin | Set it (step 3) and redeploy the backend |
| CORS error comes back after previously working | Before this was marked `sync: false`, every blueprint sync (i.e. every push) reset `VERITAS_ALLOWED_ORIGINS` back to the `render.yaml` placeholder, silently wiping your dashboard override | Re-set it on the dashboard once more — it should stick now |
| Frontend requests go to `localhost:8000` / relative `/api` 404s in production | `VITE_API_BASE_URL` wasn't set before the Vercel build | Set the env var in Vercel project settings and trigger a new deploy (it's baked in at build time, not read at runtime) |
| Render build fails installing `tensorflow`/`torch` | Same root cause as the local `.venv` gotcha in TESTING.md — these are large, platform-specific wheels | Check the build log for the actual pip error; Render's Docker builds run linux/amd64 by default, which the pinned `tensorflow-cpu` wheel supports |
| Backend crash-loops shortly after boot | If `VERITAS_CLASSIFIER_ENABLED=true`, TensorFlow alone can still be enough to OOM the free instance | Set `VERITAS_CLASSIFIER_ENABLED=false`, or upgrade to a paid instance type with more RAM |
| `/ask/stream` dies right after the `meta` event, no error, `/health` returns 502 immediately after | This was the original OOM signature from local `sentence-transformers`/PyTorch, before embeddings moved to the hosted API. Should no longer happen | If it recurs, check Render's Logs/Events for another "exceeded memory limit" — if confirmed, upgrade the instance type; there's no cheaper lever left to pull without a different architecture change |
| `ValueError: The HUGGINGFACE_API_KEY environment variable is not set` (in Render logs, surfaced to the user as a generic "something went wrong" chat error) | Secret wasn't set in step 1, or was set on a different service | Add it in the Render dashboard's Environment tab and redeploy |
| Deploy fails with "Port scan timeout reached" even though the logs show uvicorn started right after | `app.main`'s import chain was slow enough on Render's free-tier CPU to blow past the port-scan window before uvicorn could bind. Root cause found and fixed: `langchain_text_splitters`' `__init__.py` eagerly imports every splitter it ships, including one that pulls in the full torch/transformers stack, even though this project only uses the plain character splitter (`app/ingestion/chunking.py`) | Should already be fixed (the import is now deferred into the function that needs it — confirmed ~83% faster `app.main` import locally). If it recurs, profile with `python -X importtime -c "import app.main"` and defer whatever's heaviest the same way |
| Uploaded documents disappear after a while | Expected — see "Storage is ephemeral by design" above | Add a persistent disk if you need this to survive restarts |
