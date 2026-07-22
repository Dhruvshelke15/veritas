import json

import pytest

from app.eval.faithfulness import FaithfulnessJudgeError, build_judge_prompt, judge_faithfulness
from app.eval.golden import GoldenQuestion
from app.rag.pipeline import AskResult, Citation


class FakeGenerator:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, user_message: str) -> str:
        self.calls.append((system, user_message))
        return self.response


def make_question(expect_refusal: bool = False) -> GoldenQuestion:
    return GoldenQuestion(
        id="q1",
        query="How many days of unemployment are allowed?",
        category="factual",
        expect_refusal=expect_refusal,
        expected_source_files=["stem.md"],
        reference_answer="90 days",
    )


def make_result(citations: list[Citation] | None = None) -> AskResult:
    return AskResult(
        answer="You may be unemployed for up to 90 days.",
        citations=citations or [],
        sufficient_context=True,
    )


def test_parses_valid_judge_response() -> None:
    response = json.dumps({"score": 5, "rationale": "Matches the cited passage exactly."})
    score = judge_faithfulness(make_question(), make_result(), FakeGenerator(response))
    assert score.score == 5
    assert "cited passage" in score.rationale


def test_handles_fenced_output() -> None:
    inner = json.dumps({"score": 3, "rationale": "Partially supported."})
    score = judge_faithfulness(make_question(), make_result(), FakeGenerator(f"```json\n{inner}\n```"))
    assert score.score == 3


def test_rejects_out_of_range_score() -> None:
    response = json.dumps({"score": 7, "rationale": "too high"})
    with pytest.raises(FaithfulnessJudgeError, match="score"):
        judge_faithfulness(make_question(), make_result(), FakeGenerator(response))


def test_rejects_missing_rationale() -> None:
    response = json.dumps({"score": 4})
    with pytest.raises(FaithfulnessJudgeError, match="rationale"):
        judge_faithfulness(make_question(), make_result(), FakeGenerator(response))


def test_rejects_unparseable_output() -> None:
    with pytest.raises(FaithfulnessJudgeError):
        judge_faithfulness(make_question(), make_result(), FakeGenerator("not json at all"))


def test_prompt_signals_refusal_expectation() -> None:
    prompt = build_judge_prompt(make_question(expect_refusal=True), make_result())
    assert "expected to be REFUSED" in prompt


def test_prompt_includes_reference_answer_when_not_refusal() -> None:
    prompt = build_judge_prompt(make_question(expect_refusal=False), make_result())
    assert "90 days" in prompt


def test_prompt_lists_cited_passages() -> None:
    citation = Citation(
        chunk_id="doc1:0",
        text="Unemployment may not exceed 90 days.",
        source_file="stem.md",
        page=None,
        source_url=None,
        retrieved_date=None,
    )
    prompt = build_judge_prompt(make_question(), make_result(citations=[citation]))
    assert "doc1:0" in prompt
    assert "Unemployment may not exceed 90 days." in prompt


def test_prompt_notes_when_no_citations() -> None:
    prompt = build_judge_prompt(make_question(), make_result(citations=[]))
    assert "did not cite any passages" in prompt
