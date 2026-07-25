import numpy as np
import pytest
from huggingface_hub import InferenceClient

from app.config import settings
from app.ingestion import bootstrap, indexer
from app.ingestion.chunking import Chunk


@pytest.fixture(autouse=True)
def _isolated_chroma(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "chroma_dir", tmp_path / "chroma")
    monkeypatch.setattr(settings, "collection_name", "test-collection")
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "fake-token-for-tests")
    indexer._collection = None
    yield
    indexer._collection = None


def _fake_feature_extraction(self, texts):
    # Deterministic fake embedding: same text -> same vector, within this process.
    return np.array([[float(hash(t) % 97) / 97.0] * 8 for t in texts], dtype=np.float32)


def make_chunk(chunk_id: str, text: str) -> Chunk:
    doc_id, index = chunk_id.split(":")
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        metadata={"doc_id": doc_id, "source_file": f"{doc_id}.md", "chunk_index": int(index)},
    )


def test_get_collection_raises_clear_error_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("CHROMA_HUGGINGFACE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        indexer.get_collection()


def test_index_and_search_round_trip_with_mocked_hf_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(InferenceClient, "feature_extraction", _fake_feature_extraction)

    chunks = [
        make_chunk("doc1:0", "OPT allows up to 90 days of unemployment."),
        make_chunk("doc1:1", "STEM OPT extends this to 150 days total."),
    ]
    assert indexer.index_chunks(chunks) == 2

    hits = indexer.similarity_search("How many days of unemployment?", top_k=2)
    assert {h.chunk_id for h in hits} == {"doc1:0", "doc1:1"}


def test_ensure_corpus_ingested_only_seeds_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(InferenceClient, "feature_extraction", _fake_feature_extraction)
    calls: list[int] = []
    monkeypatch.setattr(bootstrap, "ingest_corpus", lambda: calls.append(1))

    bootstrap.ensure_corpus_ingested()
    assert calls == [1]

    indexer.index_chunks([make_chunk("x:0", "hello world")])
    bootstrap.ensure_corpus_ingested()
    assert calls == [1]  # collection is non-empty now, so it's not called again
