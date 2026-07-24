# Deployment

Backend and frontend deploy separately: the backend (FastAPI + ChromaDB + a TensorFlow classifier) needs a persistent server process, so it goes on **Render**; the frontend is a static Vite build, so it goes on **Vercel**. Vercel/CloudFront-style platforms can't host the backend directly — there's no serverless-function shape that fits a long-running process with a baked-in vector index and a ~1GB+ TensorFlow/PyTorch dependency tree.

Deploy the backend first — the frontend build needs its URL.

## 1. Backend on Render

1. Push this repo to GitHub (already done if you're reading this from the repo).
2. In Render: **New → Blueprint**, point it at this repo. It'll pick up [`render.yaml`](render.yaml) at the repo root, which defines a Docker web service built from [`Dockerfile`](Dockerfile).
3. Render will prompt for the one secret marked `sync: false` in `render.yaml`: set **`ANTHROPIC_API_KEY`** to your key.
4. Deploy. The build runs `pip install`, then bakes the 5 USCIS/ICE corpus docs into a ChromaDB index at build time (`scripts/ingest_corpus.py` — see the Dockerfile), so the first request after a cold start doesn't need to re-embed anything.
5. Once it's live, note the URL Render gives you (`https://<something>.onrender.com`). Confirm it works: `curl https://<something>.onrender.com/health` should return `{"status":"ok"}`.

**Storage is ephemeral by design** (see the project decision in chat): documents uploaded via `/ingest` at runtime live only as long as that container instance does, and reset on the next deploy or restart. The 5 built-in corpus docs always come back correctly because they're baked into the image, not stored on a volume. If you outgrow this, Render's paid plans support attaching a persistent disk — mount it at `data/chroma` and `data/uploads` and stop running the build-time ingestion step (or make it conditional on the directory being empty).

**Free-tier RAM warning**: TensorFlow + PyTorch (via `sentence-transformers`) + ChromaDB running together can be memory-hungry. If the service crash-loops or gets OOM-killed on Render's free instance type, that's why — move to a paid instance type with more memory.

**Cold starts**: Render's free web services spin down after inactivity. The first request after idle will be slow (container boot + model load); this is expected, not a bug.

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

## 4. Verify

Open the Vercel URL and repeat the same three checks from [TESTING.md](TESTING.md)'s browser section: ask a real question and confirm it streams and cites sources, ask an out-of-scope question and confirm it refuses, and check `/upload` and `/eval` load without console errors. A browser CORS error in the console almost always means step 3 wasn't done yet or the backend hasn't redeployed since.

## Known gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Browser console: CORS error on every `/api/*` request | `VERITAS_ALLOWED_ORIGINS` on Render doesn't include the Vercel origin | Set it (step 3) and redeploy the backend |
| Frontend requests go to `localhost:8000` / relative `/api` 404s in production | `VITE_API_BASE_URL` wasn't set before the Vercel build | Set the env var in Vercel project settings and trigger a new deploy (it's baked in at build time, not read at runtime) |
| Render build fails installing `tensorflow`/`torch` | Same root cause as the local `.venv` gotcha in TESTING.md — these are large, platform-specific wheels | Check the build log for the actual pip error; Render's Docker builds run linux/amd64 by default, which the pinned `tensorflow-cpu` wheel supports |
| Backend crash-loops shortly after boot | Likely OOM on Render's free instance (TF + PyTorch + Chroma in memory at once) | Upgrade to a paid instance type with more RAM |
| Uploaded documents disappear after a while | Expected — see "Storage is ephemeral by design" above | Add a persistent disk if you need this to survive restarts |
