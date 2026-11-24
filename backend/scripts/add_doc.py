"""Add an approved source document to the corpus and index it locally.

    python scripts/add_doc.py <url> [--title "..."] [--publisher ICE]

Writes data/corpus/<file>.md + a manifest entry (what production reseeds
from), then indexes it into the local Chroma. Commit + redeploy to ship it.
"""

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingestion.bootstrap import CORPUS_DIR, index_corpus_doc
from app.ingestion.corpus_add import CorpusAddError, add_to_corpus
from app.watch.fetch import DEFAULT_USER_AGENT


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a source document to the Veritas corpus")
    parser.add_argument("url")
    parser.add_argument("--title", default=None)
    parser.add_argument("--publisher", default="USCIS")
    parser.add_argument("--filename", default=None, help="Override the generated corpus filename (.md)")
    parser.add_argument("--no-index", action="store_true", help="Only write corpus files, skip local indexing")
    args = parser.parse_args()

    try:
        resp = httpx.get(args.url, headers={"User-Agent": DEFAULT_USER_AGENT}, follow_redirects=True, timeout=60)
        resp.raise_for_status()
        entry = add_to_corpus(
            url=args.url,
            body=resp.content,
            content_type=resp.headers.get("content-type", ""),
            corpus_dir=CORPUS_DIR,
            title=args.title,
            publisher=args.publisher,
            filename=args.filename,
        )
    except (httpx.HTTPError, CorpusAddError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Added {entry['filename']}: {entry['title']}")
    if not args.no_index:
        print(f"Indexed {index_corpus_doc(entry)} chunks into local Chroma")
    print("Review the .md, then commit data/corpus/ and redeploy to ship it.")


if __name__ == "__main__":
    main()
