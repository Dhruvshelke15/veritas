import json
from pathlib import Path

import pytest

from app.classifier.predictor import Classification
from app.eval import runner as runner_module
from app.eval.golden import GoldenQuestion
from app.eval.runner import run_eval
from app.ingestion.indexer import SearchHit


class FakeGenerator:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate(self, system: str, user_message: str) -> str:
        self.calls += 1
        return self.response


class FakeClassifier:
    def __init__(self, labels: dict[str, tuple[str, float]]) -> None:
        self._labels = labels

    def classify(self, query: str) -> Classification:
        label, confidence = self._labels[query]
        return Classification(label=label, confidence=confidence, probabilities={label: confidence})


def make_hit(source_file: str, chunk_id: str = "doc1:0") -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        text="An F-1 student may not accrue more than 90 days of unemployment.",
        distance=0.2,
        metadata={"source_file": source_file, "doc_id": "doc1", "chunk_index": 0},
    )


def answer_response() -> str:
    return json.dumps(
        {"answer": "The limit is 90 days.", "citations": ["doc1:0"], "sufficient_context": True}
    )


def judge_response(score: int = 5) -> str:
    return json.dumps({"score": score, "rationale": "Matches the cited passage."})


def patch_similarity_search(monkeypatch: pytest.MonkeyPatch, hits_by_query: dict[str, list[SearchHit]]) -> None:
    def fake_similarity_search(query: str, top_k: int) -> list[SearchHit]:
        return hits_by_query[query]

    monkeypatch.setattr(runner_module, "similarity_search", fake_similarity_search)


def test_standard_question_records_hit_and_faithfulness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    question = GoldenQuestion(
        id="q1",
        query="How many days of unemployment are allowed?",
        category="factual",
        expect_refusal=False,
        expected_source_files=["stem.md"],
        reference_answer="90 days",
    )
    patch_similarity_search(monkeypatch, {question.query: [make_hit("stem.md")]})

    report = run_eval(
        questions=[question],
        generator=FakeGenerator(answer_response()),
        judge_generator=FakeGenerator(judge_response(5)),
        classifier=None,
        top_k=4,
        db_path=tmp_path / "eval.db",
    )

    assert report.retrieval_hit_rate == 1.0
    assert report.mean_faithfulness == 5.0
    assert report.classifier_accuracy is None

    row = _fetch_question_row(tmp_path / "eval.db", "q1")
    assert row["retrieval_hit"] == 1
    assert row["faithfulness_score"] == 5
    assert row["routing_action"] == "standard"


def test_rejected_question_skips_retrieval_but_records_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    question = GoldenQuestion(
        id="q2",
        query="What is the capital of France?",
        category="out_of_scope",
        expect_refusal=True,
        expected_source_files=[],
        reference_answer="Not covered.",
    )
    patch_similarity_search(monkeypatch, {question.query: []})
    classifier = FakeClassifier({question.query: ("out_of_scope", 0.95)})
    generator = FakeGenerator(answer_response())

    report = run_eval(
        questions=[question],
        generator=generator,
        judge_generator=FakeGenerator(judge_response(5)),
        classifier=classifier,
        top_k=4,
        db_path=tmp_path / "eval.db",
    )

    assert generator.calls == 0
    assert report.retrieval_hit_rate is None
    assert report.classifier_accuracy == {"out_of_scope": 1.0}

    row = _fetch_question_row(tmp_path / "eval.db", "q2")
    assert row["routing_action"] == "reject"
    assert row["classifier_correct"] == 1


def test_unparseable_judge_output_is_recorded_without_crashing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    question = GoldenQuestion(
        id="q3",
        query="How long is STEM OPT?",
        category="factual",
        expect_refusal=False,
        expected_source_files=["stem.md"],
        reference_answer="24 months",
    )
    patch_similarity_search(monkeypatch, {question.query: [make_hit("stem.md")]})

    report = run_eval(
        questions=[question],
        generator=FakeGenerator(answer_response()),
        judge_generator=FakeGenerator("not json at all"),
        classifier=None,
        top_k=4,
        db_path=tmp_path / "eval.db",
    )

    assert report.mean_faithfulness is None
    row = _fetch_question_row(tmp_path / "eval.db", "q3")
    assert row["faithfulness_score"] is None
    assert "judge error" in row["faithfulness_rationale"]


def _fetch_question_row(db_path: Path, question_id: str) -> dict:
    from app.eval import storage

    conn = storage.connect(db_path)
    conn.row_factory = None
    cursor = conn.execute(
        "SELECT retrieval_hit, faithfulness_score, faithfulness_rationale, "
        "classifier_correct, routing_action FROM eval_question_results WHERE question_id = ?",
        (question_id,),
    )
    columns = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row, strict=True))
