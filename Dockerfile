# Backend image only — the frontend is a static build meant for Vercel/Netlify/etc.
# Deployed on Google Cloud Run (see DEPLOYMENT.md) via `gcloud run deploy
# --source .`, which builds this Dockerfile with Cloud Build and pushes it
# for you — no manual `docker build`/`push` needed. Build context is the
# repo root (needs both backend/ and data/).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# chromadb/sentence-transformers/tensorflow pull in a few deps that may not
# ship prebuilt wheels for every platform; build-essential is cheap insurance
# against a from-source build failing partway through `pip install`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
COPY data/ data/

WORKDIR /app/backend

# Corpus ingestion happens lazily at runtime on first request instead of
# here at build time (see app/ingestion/bootstrap.py): embeddings are now
# computed via a hosted API (HUGGINGFACE_API_KEY), and that credential is
# only available as a runtime env var, not during `docker build`.

EXPOSE 8000

# $PORT is injected by Cloud Run (and most other PaaS); falls back to 8000
# for a plain `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
