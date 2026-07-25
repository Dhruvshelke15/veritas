# Deployment

Backend and frontend deploy separately: the backend (FastAPI + ChromaDB, optionally a TensorFlow classifier) needs a persistent server process, so it goes on **Google Cloud Run**; the frontend is a static Vite build, so it goes on **Vercel**.

Deploy the backend first — the frontend build needs its URL.

## 0. Why Cloud Run, not Render

This project was originally deployed on Render's free tier and moved off it after four separate reliability incidents in one deployment cycle: repeated OOM kills (PyTorch + ChromaDB + Claude client resident at once), a `render.yaml` blueprint sync silently overwriting a manually-set CORS env var, and two unrelated request hangs. The common thread wasn't Render specifically — it's that free tiers on most PaaS platforms throttle CPU and cap memory hard enough that this app's dependency footprint (even after trimming PyTorch out of the hot path) sits right at the edge of what's viable. See `docs/design-decisions.md` for the full incident history.

Cloud Run's relevant advantages for this app: real (non-shared-throttled) CPU during request handling, a free tier generous enough that a low-traffic personal project likely never bills, `--min-instances` to eliminate cold starts entirely if wanted, and env var changes applied via `gcloud`/console are authoritative — no separate config file that can silently overwrite a dashboard value the way `render.yaml` did.

## 1. Backend on Google Cloud Run

One-time setup:

```bash
brew install --cask google-cloud-sdk   # if not already installed
gcloud auth login                       # opens a browser
gcloud projects create YOUR_PROJECT_ID --name="Veritas"
gcloud config set project YOUR_PROJECT_ID
gcloud billing projects link YOUR_PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

(`gcloud billing accounts list` shows your billing account IDs if you don't have one handy. Cloud Run requires billing enabled on the project even to use the free tier — you're not charged unless you exceed it.)

Deploy, from the repo root:

```bash
gcloud run deploy veritas-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 300 \
  --set-env-vars "VERITAS_CLASSIFIER_ENABLED=false,VERITAS_ALLOWED_ORIGINS=http://localhost:5173,ANTHROPIC_API_KEY=sk-ant-...,HUGGINGFACE_API_KEY=hf_..."
```

`--source .` builds the [`Dockerfile`](Dockerfile) at the repo root via Cloud Build and pushes it to Artifact Registry automatically — no manual `docker build`/`push`. **The first deploy's build takes 10+ minutes** (installing `tensorflow`/`torch`/`chromadb` from scratch, no layer cache yet); this timed out a plain terminal wait more than once during initial setup. If it does, the build itself keeps running server-side regardless — check `gcloud builds list --region us-central1` for `SUCCESS`, then deploy the already-built image directly (fast, no rebuild) instead of re-running `--source .`:

```bash
gcloud run deploy veritas-backend \
  --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/cloud-run-source-deploy/veritas-backend \
  --region us-central1 \
  --allow-unauthenticated --memory 1Gi --cpu 1 --min-instances 0 --max-instances 3 --timeout 300 \
  --set-env-vars "..."
```

Once live, `gcloud run services describe veritas-backend --region us-central1 --format="value(status.url)"` prints the service URL. Confirm it: `curl <url>/health` should return `{"status":"ok"}`.

**Storage is ephemeral by design**: documents uploaded via `/ingest`, and the seeded corpus itself, live only as long as that container instance does, and get re-seeded from scratch on the next revision or cold start (fast — it's a hosted-API HTTP call now, not a local model load; see `app/ingestion/bootstrap.py`). Cloud Run supports mounting a persistent volume (Cloud Storage FUSE or a Filestore-backed volume) if you outgrow this.

**Cold starts**: with `--min-instances 0` (the default above, cheapest), Cloud Run scales to zero after inactivity and the next request pays a cold-start cost, including re-seeding the corpus. If that's ever annoying, `gcloud run services update veritas-backend --region us-central1 --min-instances 1` keeps one instance warm permanently (small ongoing cost — check current Cloud Run pricing before enabling).

## 2. Frontend on Vercel

1. In Vercel: **New Project**, import this repo, set **Root Directory** to `frontend`.
2. Framework preset should auto-detect Vite. Build command `npm run build`, output directory `dist` (Vercel defaults are already correct).
3. Add an environment variable: **`VITE_API_BASE_URL`** = the Cloud Run URL from step 1 (e.g. `https://veritas-backend-xxxxx-uc.a.run.app`, no trailing slash). This is read at *build* time (see `frontend/src/api/client.ts`) — changing it later requires a redeploy, not just a restart.
4. Deploy. [`vercel.json`](frontend/vercel.json) handles SPA routing so refreshing on `/upload` or `/eval` doesn't 404.

## 3. Close the loop: CORS

The backend only accepts requests from origins listed in `VERITAS_ALLOWED_ORIGINS` (comma-separated; see `app/config.py`). Once you have the Vercel URL:

```bash
gcloud run services update veritas-backend \
  --region us-central1 \
  --update-env-vars "VERITAS_ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app,http://localhost:5173"
```

Unlike Render's blueprint sync, this value is only ever changed by an explicit `gcloud`/console action — there's no config file that silently resets it on every deploy.

## 4. Verify

Open the Vercel URL and repeat the same three checks from [TESTING.md](TESTING.md)'s browser section: ask a real question and confirm it streams and cites sources, ask an out-of-scope question and confirm it refuses, and check `/upload` and `/eval` load without console errors. A browser CORS error in the console almost always means step 3 wasn't done yet, or the backend hasn't picked up the env var change (`gcloud run services update` deploys a new revision automatically, but give it a few seconds).

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
| Browser console: CORS error on every `/api/*` request | `VERITAS_ALLOWED_ORIGINS` on Cloud Run doesn't include the Vercel origin | Set it (step 3) |
| Frontend requests go to `localhost:8000` / relative `/api` 404s in production | `VITE_API_BASE_URL` wasn't set before the Vercel build | Set the env var in Vercel project settings and trigger a new deploy (it's baked in at build time, not read at runtime) |
| `gcloud run deploy --source .` seems to hang / your terminal times out | First build (no layer cache) genuinely takes 10+ minutes | Check `gcloud builds list --region us-central1` — if `SUCCESS`, deploy the already-built image directly (see step 1) instead of re-running `--source .` |
| `ValueError: The HUGGINGFACE_API_KEY environment variable is not set` (surfaced to the user as a generic "something went wrong" chat error) | Env var wasn't set, or was set on a different service/revision | `gcloud run services update veritas-backend --region us-central1 --update-env-vars HUGGINGFACE_API_KEY=hf_...` |
| `/ask/stream` hangs for a while (not indefinitely — bounded to ~45s) after the `meta` event | `huggingface_hub.InferenceClient` waiting on a slow/cold response from HF during first-request corpus seeding | Expected occasionally on a cold start; `app/ingestion/embeddings.py` bounds this to 45s so it fails with a real error rather than hanging forever. If it's consistently slow, `--min-instances 1` avoids the cold-seeding path being hit as often |
| Uploaded documents disappear after a while | Expected — see "Storage is ephemeral by design" above | Mount a persistent volume if you need this to survive restarts |
| `/ask/stream` returns a clean "Something went wrong" error; logs show `huggingface_hub.errors.HfHubHTTPError: ... 429 Too Many Requests` from `huggingface.co/api/models/...` | HF rate-limited the one-time model-metadata lookup `huggingface_hub` does on a cold start (separate from the actual embedding call, cached per-process afterward via `@lru_cache`) — usually from bursty testing against the same token, not a structural problem | Just retry — confirmed transient in practice, resolves within seconds. If it's persistent, it's a token-level rate limit worth checking on HF's side |
