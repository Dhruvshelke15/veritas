import json
from datetime import date

from app.config import settings
from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import get_collection, index_chunks
from app.ingestion.loaders import load_document


def ingest_corpus() -> None:
    corpus_dir = settings.golden_set_path.parent.parent / "corpus"
    manifest = json.loads((corpus_dir / "manifest.json").read_text())
    for doc in manifest["documents"]:
        filename = doc["filename"]
        if not filename.endswith(".md"):
            continue
        path = corpus_dir / filename
        doc_id = compute_doc_id(path.read_bytes())
        docs = load_document(path)
        chunks = chunk_documents(docs, doc_id, source_url=doc["source_url"], retrieved_date=date.today().isoformat())
        index_chunks(chunks)
        print(f"Indexed {filename} ({len(chunks)} chunks)")


def ensure_corpus_ingested() -> None:
    """Seed the built-in corpus on first use if the collection is empty.

    With embeddings now computed via a hosted API instead of a local model,
    baking the index into the Docker image at build time would need a
    build-time secret. Simpler and just as fast in practice: seed lazily,
    once, the first time something actually queries or lists documents.
    """
    if get_collection().count() == 0:
        ingest_corpus()
