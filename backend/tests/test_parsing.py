import pytest

from app.rag.parsing import (
    AnswerParseError,
    ParsedAnswer,
    parse_answer,
    validate_citations,
)

VALID_JSON = '{"answer": "Pods are the smallest unit.", "citations": ["abc:0"], "sufficient_context": true}'


def test_parses_clean_json() -> None:
    parsed = parse_answer(VALID_JSON)
    assert parsed.answer == "Pods are the smallest unit."
    assert parsed.citations == ["abc:0"]
    assert parsed.sufficient_context is True


def test_parses_json_fenced_with_language_tag() -> None:
    raw = f"```json\n{VALID_JSON}\n```"
    parsed = parse_answer(raw)
    assert parsed.citations == ["abc:0"]


def test_parses_json_fenced_without_language_tag() -> None:
    raw = f"```\n{VALID_JSON}\n```"
    parsed = parse_answer(raw)
    assert parsed.answer.startswith("Pods")


def test_parses_json_with_surrounding_prose() -> None:
    raw = f"Here is the answer you requested:\n{VALID_JSON}\nLet me know if you need more."
    parsed = parse_answer(raw)
    assert parsed.sufficient_context is True


def test_parses_refusal_shape() -> None:
    raw = '{"answer": "The documents do not cover this.", "citations": [], "sufficient_context": false}'
    parsed = parse_answer(raw)
    assert parsed.sufficient_context is False
    assert parsed.citations == []


def test_rejects_output_with_no_json() -> None:
    with pytest.raises(AnswerParseError) as exc_info:
        parse_answer("I cannot answer that question.")
    assert exc_info.value.raw == "I cannot answer that question."


def test_rejects_malformed_json() -> None:
    with pytest.raises(AnswerParseError):
        parse_answer('{"answer": "truncated...')


def test_rejects_missing_answer_field() -> None:
    with pytest.raises(AnswerParseError):
        parse_answer('{"citations": [], "sufficient_context": true}')


def test_rejects_non_boolean_sufficient_context() -> None:
    with pytest.raises(AnswerParseError):
        parse_answer('{"answer": "x", "citations": [], "sufficient_context": "yes"}')


def test_rejects_non_list_citations() -> None:
    with pytest.raises(AnswerParseError):
        parse_answer('{"answer": "x", "citations": "abc:0", "sufficient_context": true}')


def test_validate_citations_filters_hallucinated_ids() -> None:
    parsed = ParsedAnswer(
        answer="x", citations=["real:0", "fake:9", "real:1"], sufficient_context=True
    )
    valid, hallucinated = validate_citations(parsed, {"real:0", "real:1", "real:2"})
    assert valid == ["real:0", "real:1"]
    assert hallucinated == ["fake:9"]


def test_validate_citations_all_valid() -> None:
    parsed = ParsedAnswer(answer="x", citations=["a:0"], sufficient_context=True)
    valid, hallucinated = validate_citations(parsed, {"a:0"})
    assert valid == ["a:0"]
    assert hallucinated == []
