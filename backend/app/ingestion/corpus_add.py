"""Turn a fetched source document into a persisted corpus entry.

Production rebuilds its index from data/corpus/manifest.json on every cold
start, so the corpus (not the /ingest endpoint) is the only place an addition
survives. This does what used to be manual: convert to markdown, write the
file, append the manifest entry.
"""

import io
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import html2text
from bs4 import BeautifulSoup
from pypdf import PdfReader


class CorpusAddError(ValueError):
    pass


def html_to_markdown(html: str) -> tuple[str, str]:
    """Same conversion data/corpus/convert.py used for the seed corpus."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    main = soup.find("main") or soup.find("article") or soup.body or soup
    for tag in main.find_all(["nav", "script", "style", "aside", "form", "noscript"]):
        tag.decompose()
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    return h.handle(str(main)), title.split("|")[0].strip()


def pdf_to_markdown(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def slugify(url: str, publisher: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    stem = Path(parts[-1]).stem if parts else "document"
    return f"{publisher.lower()}_{re.sub(r'[^a-z0-9]+', '_', stem.lower()).strip('_')[:80]}.md"


def add_to_corpus(
    *,
    url: str,
    body: bytes,
    content_type: str,
    corpus_dir: Path,
    title: str | None = None,
    publisher: str = "USCIS",
    filename: str | None = None,
) -> dict:
    manifest_path = corpus_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if any(d["source_url"] == url for d in manifest["documents"]):
        raise CorpusAddError(f"Already in corpus: {url}")

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        markdown, page_title = pdf_to_markdown(body), ""
    else:
        markdown, page_title = html_to_markdown(body.decode("utf-8", errors="replace"))

    # A bot-block interstitial or an empty scanned PDF would otherwise land in
    # the corpus looking like a real source and silently poison retrieval.
    if len(markdown.strip()) < 500:
        raise CorpusAddError(f"Only {len(markdown.strip())} chars extracted from {url}; refusing to add.")

    filename = filename or slugify(url, publisher)
    if (corpus_dir / filename).exists():
        raise CorpusAddError(f"{filename} already exists; pass a different --filename.")

    entry = {
        "filename": filename,
        "title": title or page_title or filename,
        "source_url": url,
        "publisher": publisher,
    }
    (corpus_dir / filename).write_text(markdown, encoding="utf-8")
    manifest["documents"].append(entry)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return entry
