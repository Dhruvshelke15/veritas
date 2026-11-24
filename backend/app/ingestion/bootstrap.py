import json
from datetime import date
from pathlib import Path

from app.config import settings
from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import get_collection, index_chunks
from app.ingestion.loaders import load_document

CORPUS_DIR = settings.golden_set_path.parent.parent / "corpus"


def index_corpus_doc(doc: dict, corpus_dir: Path = CORPUS_DIR) -> int:
    path = corpus_dir / doc["filename"]
    doc_id = compute_doc_id(path.read_bytes())
    chunks = chunk_documents(
        load_document(path), doc_id, source_url=doc["source_url"], retrieved_date=date.today().isoformat()
    )
    return index_chunks(chunks)


def ingest_corpus() -> None:
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text())
    for doc in manifest["documents"]:
        if not doc["filename"].endswith(".md"):
            continue
        print(f"Indexed {doc['filename']} ({index_corpus_doc(doc)} chunks)")


def ensure_corpus_ingested() -> None:
    """Seed the built-in corpus on first use if the collection is empty.

    With embeddings now computed via a hosted API instead of a local model,
    baking the index into the Docker image at build time would need a
    build-time secret. Simpler and just as fast in practice: seed lazily,
    once, the first time something actually queries or lists documents.
    """
    if get_collection().count() == 0:
        ingest_corpus()
