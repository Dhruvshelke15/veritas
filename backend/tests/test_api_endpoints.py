import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.eval import storage as eval_storage
from app.ingestion.indexer import SearchHit


@pytest.fixture()
def client() -> TestClient:
    return TestClient(main.app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_documents_endpoint_returns_list(client: TestClient) -> None:
    response = client.get("/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_eval_runs_empty_when_no_db(client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.settings, "eval_db_path", tmp_path / "eval.db")
    response = client.get("/eval/runs")
    assert response.status_code == 200
    assert response.json() == []


def test_eval_run_detail_404_for_missing_run(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(main.settings, "eval_db_path", tmp_path / "eval.db")
    response = client.get("/eval/runs/999")
    assert response.status_code == 404


def test_eval_run_detail_returns_populated_run(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "eval.db"
    monkeypatch.setattr(main.settings, "eval_db_path", db_path)
    conn = eval_storage.connect(db_path)
    run_id = eval_storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    eval_storage.finalize_run(conn, run_id, 1.0, 5.0, {"factual": 1.0})

    response = client.get(f"/eval/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["run_id"] == run_id
    assert body["questions"] == []


class FakeStreamingGenerator:
    def __init__(self, response: str) -> None:
        self.response = response

    def generate_stream(self, system: str, user_message: str):
        yield self.response


def make_hit() -> SearchHit:
    return SearchHit(
        chunk_id="doc1:0",
        text="An F-1 student may not accrue more than 90 days of unemployment.",
        distance=0.2,
        metadata={"source_file": "policy.md", "doc_id": "doc1", "chunk_index": 0},
    )


def test_ask_stream_emits_meta_deltas_and_final(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    response_json = json.dumps(
        {"answer": "Up to 90 days.", "citations": [], "sufficient_context": False}
    )
    monkeypatch.setattr(main, "get_classifier", lambda: None)
    monkeypatch.setattr(main, "get_generator", lambda: FakeStreamingGenerator(response_json))
    monkeypatch.setattr("app.rag.pipeline.similarity_search", lambda query, top_k: [make_hit()])

    with client.stream(
        "POST", "/ask/stream", json={"query": "How many days of unemployment are allowed?"}
    ) as response:
        assert response.status_code == 200
        events = [
            json.loads(line[len("data: ") :])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    types = [e["type"] for e in events]
    assert types[0] == "meta"
    assert types[-1] == "final"
    final = events[-1]
    assert final["answer"] == "Up to 90 days."
