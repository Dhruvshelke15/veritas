import numpy as np
import pytest
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from app.config import settings
from app.ingestion import bootstrap, indexer
from app.ingestion.chunking import Chunk


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "chroma_dir", tmp_path / "chroma")
    monkeypatch.setattr(settings, "collection_name", "test-collection")
    indexer._collection = None
    yield
    indexer._collection = None


def _fake_embed(self, input):
    # Deterministic fake embedding: same text -> same vector, within this process.
    return np.array([[float(hash(t) % 97) / 97.0] * 8 for t in input], dtype=np.float32)


def make_chunk(chunk_id: str, text: str) -> Chunk:
    doc_id, index = chunk_id.split(":")
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        metadata={"doc_id": doc_id, "source_file": f"{doc_id}.md", "chunk_index": int(index)},
    )


def test_index_and_search_round_trip_with_mocked_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ONNXMiniLM_L6_V2, "__call__", _fake_embed)

    chunks = [
        make_chunk("doc1:0", "OPT allows up to 90 days of unemployment."),
        make_chunk("doc1:1", "STEM OPT extends this to 150 days total."),
    ]
    assert indexer.index_chunks(chunks) == 2

    hits = indexer.similarity_search("How many days of unemployment?", top_k=2)
    assert {h.chunk_id for h in hits} == {"doc1:0", "doc1:1"}


def test_ensure_corpus_ingested_only_seeds_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ONNXMiniLM_L6_V2, "__call__", _fake_embed)
    calls: list[int] = []
    monkeypatch.setattr(bootstrap, "ingest_corpus", lambda: calls.append(1))

    bootstrap.ensure_corpus_ingested()
    assert calls == [1]

    indexer.index_chunks([make_chunk("x:0", "hello world")])
    bootstrap.ensure_corpus_ingested()
    assert calls == [1]  # collection is non-empty now, so it's not called again
