from langchain_core.documents import Document

from app.config import settings
from app.ingestion.chunking import chunk_documents, compute_doc_id


def make_doc(text: str) -> Document:
    return Document(page_content=text, metadata={"source_file": "test.md"})


def test_doc_id_is_deterministic() -> None:
    assert compute_doc_id(b"hello world") == compute_doc_id(b"hello world")
    assert compute_doc_id(b"hello world") != compute_doc_id(b"hello world!")
    assert len(compute_doc_id(b"anything")) == 12


def test_chunk_ids_are_sequential_and_prefixed() -> None:
    text = "Paragraph one.\n\n" + ("Filler sentence about topics. " * 100)
    chunks = chunk_documents([make_doc(text)], doc_id="abc123def456")
    assert len(chunks) > 1
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_id == f"abc123def456:{i}"
        assert chunk.metadata["chunk_index"] == i


def test_chunks_respect_size_limit() -> None:
    text = "Word " * 2000
    chunks = chunk_documents([make_doc(text)], doc_id="d" * 12)
    assert all(len(c.text) <= settings.chunk_size for c in chunks)


def test_overlap_preserves_boundary_content() -> None:
    sentences = [f"Fact number {i} lives in this sentence." for i in range(60)]
    text = " ".join(sentences)
    chunks = chunk_documents([make_doc(text)], doc_id="e" * 12)
    assert len(chunks) > 1
    joined = " ".join(c.text for c in chunks)
    for sentence in sentences:
        assert sentence in joined


def test_short_document_yields_single_chunk() -> None:
    chunks = chunk_documents([make_doc("Just one short paragraph.")], doc_id="f" * 12)
    assert len(chunks) == 1
    assert chunks[0].text == "Just one short paragraph."


def test_metadata_carries_source_file() -> None:
    chunks = chunk_documents([make_doc("Some content here.")], doc_id="a" * 12)
    assert chunks[0].metadata["source_file"] == "test.md"


def test_source_url_and_retrieved_date_propagate() -> None:
    chunks = chunk_documents(
        [make_doc("Content about OPT.")],
        doc_id="b" * 12,
        source_url="https://www.uscis.gov/example",
        retrieved_date="2026-07-14",
    )
    assert chunks[0].metadata["source_url"] == "https://www.uscis.gov/example"
    assert chunks[0].metadata["retrieved_date"] == "2026-07-14"


def test_freshness_metadata_absent_when_not_provided() -> None:
    chunks = chunk_documents([make_doc("Content.")], doc_id="c" * 12)
    assert "source_url" not in chunks[0].metadata
    assert "retrieved_date" not in chunks[0].metadata
