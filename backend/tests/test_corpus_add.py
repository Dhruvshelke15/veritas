import json

import pytest

from app.ingestion.corpus_add import CorpusAddError, add_to_corpus

URL = "https://www.uscis.gov/working-in-the-united-states/new-opt-guidance"
HTML = (
    "<html><head><title>New OPT Guidance | USCIS</title></head><body>"
    "<nav>skip me</nav><main><h1>New OPT Guidance</h1><p>" + "OPT detail. " * 100 + "</p></main></body></html>"
).encode()


def test_add_to_corpus_writes_markdown_and_manifest(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"documents": []}))

    entry = add_to_corpus(url=URL, body=HTML, content_type="text/html", corpus_dir=tmp_path)

    assert entry == {
        "filename": "uscis_new_opt_guidance.md",
        "title": "New OPT Guidance",
        "source_url": URL,
        "publisher": "USCIS",
    }
    md = (tmp_path / entry["filename"]).read_text()
    assert "# New OPT Guidance" in md and "skip me" not in md
    assert json.loads((tmp_path / "manifest.json").read_text())["documents"] == [entry]

    with pytest.raises(CorpusAddError, match="Already in corpus"):
        add_to_corpus(url=URL, body=HTML, content_type="text/html", corpus_dir=tmp_path)


def test_near_empty_page_is_refused(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"documents": []}))
    with pytest.raises(CorpusAddError, match="refusing"):
        add_to_corpus(url=URL, body=b"<html><body>Access Denied</body></html>", content_type="text/html", corpus_dir=tmp_path)
    assert not list(tmp_path.glob("*.md"))
