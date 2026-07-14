import json
import re
from dataclasses import dataclass

FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class AnswerParseError(ValueError):
    def __init__(self, message: str, raw: str) -> None:
        super().__init__(message)
        self.raw = raw


@dataclass(frozen=True)
class ParsedAnswer:
    answer: str
    citations: list[str]
    sufficient_context: bool


def extract_json_payload(raw: str) -> str:
    text = raw.strip()
    fence_match = FENCE_PATTERN.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AnswerParseError("No JSON object found in model output", raw)
    return text[start : end + 1]


def parse_answer(raw: str) -> ParsedAnswer:
    payload = extract_json_payload(raw)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AnswerParseError(f"Invalid JSON in model output: {exc}", raw) from exc

    if not isinstance(data, dict):
        raise AnswerParseError("Model output JSON is not an object", raw)

    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise AnswerParseError("Missing or empty 'answer' field", raw)

    citations_raw = data.get("citations", [])
    if not isinstance(citations_raw, list):
        raise AnswerParseError("'citations' is not a list", raw)
    citations = [str(c) for c in citations_raw]

    sufficient = data.get("sufficient_context")
    if not isinstance(sufficient, bool):
        raise AnswerParseError("Missing or non-boolean 'sufficient_context' field", raw)

    return ParsedAnswer(answer=answer.strip(), citations=citations, sufficient_context=sufficient)


def validate_citations(parsed: ParsedAnswer, retrieved_ids: set[str]) -> tuple[list[str], list[str]]:
    valid = [c for c in parsed.citations if c in retrieved_ids]
    hallucinated = [c for c in parsed.citations if c not in retrieved_ids]
    return valid, hallucinated
