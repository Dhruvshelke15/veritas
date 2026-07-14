import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import index_chunks, similarity_search
from app.ingestion.loaders import load_document


def cmd_ingest(path_str: str, source_url: str | None) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    doc_id = compute_doc_id(path.read_bytes())
    docs = load_document(path)
    chunks = chunk_documents(
        docs, doc_id, source_url=source_url, retrieved_date=date.today().isoformat()
    )
    count = index_chunks(chunks)

    print(f"doc_id: {doc_id}")
    print(f"pages loaded: {len(docs)}")
    print(f"chunks indexed: {count}")
    sizes = [len(c.text) for c in chunks]
    if sizes:
        print(f"chunk sizes: min={min(sizes)} max={max(sizes)} avg={sum(sizes) // len(sizes)}")


def cmd_search(query: str, top_k: int) -> None:
    hits = similarity_search(query, top_k=top_k)
    if not hits:
        print("No results. Ingest a document first.")
        return
    for rank, hit in enumerate(hits, start=1):
        print(f"\n[{rank}] chunk_id={hit.chunk_id} distance={hit.distance:.4f}")
        print(f"    source={hit.metadata.get('source_file')} page={hit.metadata.get('page', '-')}")
        preview = hit.text.replace("\n", " ")
        print(f"    {preview[:240]}{'...' if len(preview) > 240 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Veritas ingestion CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("path")
    p_ingest.add_argument("--source-url", default=None)

    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--top-k", type=int, default=4)

    args = parser.parse_args()
    if args.command == "ingest":
        cmd_ingest(args.path, args.source_url)
    else:
        cmd_search(args.query, args.top_k)


if __name__ == "__main__":
    main()
