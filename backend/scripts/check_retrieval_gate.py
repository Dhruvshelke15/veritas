import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.eval.golden import load_golden_set
from app.eval.retrieval import hit_rate, retrieval_hit
from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import index_chunks, similarity_search
from app.ingestion.loaders import load_document


def ingest_corpus() -> None:
    manifest = json.loads((settings.golden_set_path.parent.parent / "corpus" / "manifest.json").read_text())
    corpus_dir = settings.golden_set_path.parent.parent / "corpus"
    for doc in manifest["documents"]:
        filename = doc["filename"]
        if not filename.endswith(".md"):
            continue
        path = corpus_dir / filename
        doc_id = compute_doc_id(path.read_bytes())
        docs = load_document(path)
        chunks = chunk_documents(
            docs, doc_id, source_url=doc["source_url"], retrieved_date=date.today().isoformat()
        )
        index_chunks(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail the build if retrieval hit rate drops below a threshold")
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    print("Ingesting corpus...")
    ingest_corpus()

    questions = load_golden_set(settings.golden_set_path)
    top_k = args.top_k or settings.default_top_k

    results: list[bool | None] = []
    misses: list[str] = []
    for question in questions:
        hits = similarity_search(question.query, top_k=top_k)
        hit = retrieval_hit(question, hits)
        results.append(hit)
        if hit is False:
            misses.append(question.id)

    rate = hit_rate(results)
    applicable = sum(1 for r in results if r is not None)
    print(f"Retrieval hit rate: {rate:.3f} ({applicable - len(misses)}/{applicable} applicable questions)")
    if misses:
        print(f"Misses: {misses}")

    if rate is None:
        print("No applicable questions to score (all golden questions have no expected source).")
        sys.exit(1)

    if rate < args.threshold:
        print(f"FAIL: retrieval hit rate {rate:.3f} is below threshold {args.threshold:.3f}")
        sys.exit(1)

    print(f"PASS: retrieval hit rate {rate:.3f} meets threshold {args.threshold:.3f}")


if __name__ == "__main__":
    main()
