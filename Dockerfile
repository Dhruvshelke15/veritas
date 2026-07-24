# Backend image only — the frontend is a static build meant for Vercel/Netlify/etc.
# Build context is the repo root (needs both backend/ and data/), e.g.:
#   docker build -f Dockerfile -t veritas-backend .

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

# Bakes the 5 USCIS/ICE corpus docs into the image as a populated ChromaDB
# directory, so a fresh container serves real answers immediately instead of
# re-embedding on every cold start. Corpus changes require a rebuild+redeploy
# to take effect — by design, matching how corpus updates flow through git.
RUN python scripts/ingest_corpus.py

EXPOSE 8000

# $PORT is injected by most PaaS (Render, Railway, ...); falls back to 8000
# for a plain `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
