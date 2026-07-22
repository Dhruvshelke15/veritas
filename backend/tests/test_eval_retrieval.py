import pytest

from app.eval.golden import GoldenQuestion
from app.eval.retrieval import hit_rate, retrieval_hit
from app.ingestion.indexer import SearchHit


def make_question(expected_source_files: list[str]) -> GoldenQuestion:
    return GoldenQuestion(
        id="q1",
        query="How many days?",
        category="factual",
        expect_refusal=False,
        expected_source_files=expected_source_files,
        reference_answer="90 days",
    )


def make_hit(source_file: str) -> SearchHit:
    return SearchHit(
        chunk_id=f"{source_file}:0",
        text="some text",
        distance=0.1,
        metadata={"source_file": source_file},
    )


def test_hit_when_expected_source_present() -> None:
    question = make_question(["opt.md", "stem.md"])
    hits = [make_hit("other.md"), make_hit("stem.md")]
    assert retrieval_hit(question, hits) is True


def test_miss_when_expected_source_absent() -> None:
    question = make_question(["opt.md"])
    hits = [make_hit("other.md")]
    assert retrieval_hit(question, hits) is False


def test_none_when_no_expected_sources() -> None:
    question = make_question([])
    hits = [make_hit("other.md")]
    assert retrieval_hit(question, hits) is None


def test_miss_when_no_hits_at_all() -> None:
    question = make_question(["opt.md"])
    assert retrieval_hit(question, []) is False


def test_hit_rate_aggregates_only_applicable_results() -> None:
    results = [True, False, None, True]
    assert hit_rate(results) == pytest.approx(2 / 3)


def test_hit_rate_none_when_nothing_applicable() -> None:
    assert hit_rate([None, None]) is None


def test_hit_rate_empty_list() -> None:
    assert hit_rate([]) is None
