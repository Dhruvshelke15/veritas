import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import index_chunks
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


if __name__ == "__main__":
    print("Ingesting corpus...")
    ingest_corpus()
    print("Done.")
