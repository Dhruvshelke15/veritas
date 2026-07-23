import re
from dataclasses import dataclass, replace
from typing import Iterator, Union

from app.classifier.predictor import Classification
from app.config import settings
from app.ingestion.indexer import SearchHit
from app.rag.generator import StreamingGenerator
from app.rag.parsing import AnswerParseError, parse_answer, validate_citations
from app.rag.pipeline import (
    NO_RESULTS_ANSWER,
    PARSE_FAILURE_ANSWER,
    AskResult,
    Retriever,
    default_retriever,
    to_citation,
)
from app.rag.prompt import SYSTEM_PROMPT, build_user_message
from app.rag.routing import ADVICE_DISCLAIMER, OUT_OF_SCOPE_ANSWER, route

ANSWER_KEY_PATTERN = re.compile(r'"answer"\s*:\s*"')

ESCAPE_MAP = {'"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}


def _decode_json_string_prefix(raw: str, start: int) -> tuple[str, int, bool]:
    """Decode as much of a JSON string value as is safely decodable.

    Returns (decoded_text, position_after_last_consumed_char, closed).
    Stops at an unescaped closing quote (closed=True) or at the end of
    available text, holding back an incomplete trailing escape sequence
    rather than mis-decoding it.
    """
    out: list[str] = []
    i = start
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == '"':
            return "".join(out), i + 1, True
        if ch == "\\":
            if i + 1 >= n:
                break
            esc = raw[i + 1]
            if esc == "u":
                if i + 6 > n:
                    break
                out.append(chr(int(raw[i + 2 : i + 6], 16)))
                i += 6
                continue
            if esc in ESCAPE_MAP:
                out.append(ESCAPE_MAP[esc])
                i += 2
                continue
            # Unrecognized escape: pass the literal character through.
            out.append(esc)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out), i, False


class AnswerStreamDecoder:
    """Incrementally extracts the growing 'answer' field value from a
    partially-received JSON blob, before the object is complete or valid."""

    def __init__(self) -> None:
        self._raw = ""
        self._answer_start: int | None = None
        self._decoded_emitted = 0
        self._closed = False

    def feed(self, chunk: str) -> str:
        self._raw += chunk
        if self._closed:
            return ""
        if self._answer_start is None:
            match = ANSWER_KEY_PATTERN.search(self._raw)
            if not match:
                return ""
            self._answer_start = match.end()
        decoded, _end, closed = _decode_json_string_prefix(self._raw, self._answer_start)
        self._closed = closed
        new_text = decoded[self._decoded_emitted :]
        self._decoded_emitted = len(decoded)
        return new_text


@dataclass(frozen=True)
class MetaEvent:
    query_category: str | None
    category_confidence: float | None
    routing_action: str


@dataclass(frozen=True)
class AnswerDeltaEvent:
    text: str


@dataclass(frozen=True)
class FinalEvent:
    result: AskResult


StreamEvent = Union[MetaEvent, AnswerDeltaEvent, FinalEvent]


def _parse_raw(raw: str, hits: list[SearchHit]) -> AskResult:
    try:
        parsed = parse_answer(raw)
    except AnswerParseError:
        return AskResult(
            answer=PARSE_FAILURE_ANSWER,
            citations=[],
            sufficient_context=False,
            parse_failed=True,
        )

    hits_by_id = {h.chunk_id: h for h in hits}
    valid_ids, hallucinated = validate_citations(parsed, set(hits_by_id))

    if parsed.sufficient_context and not valid_ids:
        return AskResult(
            answer=parsed.answer,
            citations=[],
            sufficient_context=False,
            hallucinated_citations=hallucinated,
        )

    citations = [to_citation(hits_by_id[cid]) for cid in valid_ids]
    return AskResult(
        answer=parsed.answer,
        citations=citations,
        sufficient_context=parsed.sufficient_context,
        hallucinated_citations=hallucinated,
    )


def ask_routed_stream(
    query: str,
    generator: StreamingGenerator,
    classification: Classification | None,
    top_k: int | None = None,
    retriever: Retriever = default_retriever,
) -> Iterator[StreamEvent]:
    decision = route(classification)
    yield MetaEvent(
        query_category=decision.category,
        category_confidence=decision.confidence,
        routing_action=decision.action,
    )

    if decision.action == "reject":
        yield FinalEvent(
            AskResult(
                answer=OUT_OF_SCOPE_ANSWER,
                citations=[],
                sufficient_context=False,
                query_category=decision.category,
                category_confidence=decision.confidence,
                routing_action="reject",
            )
        )
        return

    hits: list[SearchHit] = retriever(query, top_k or settings.default_top_k)
    if not hits:
        yield FinalEvent(
            replace(
                AskResult(answer=NO_RESULTS_ANSWER, citations=[], sufficient_context=False),
                query_category=decision.category,
                category_confidence=decision.confidence,
                routing_action=decision.action,
            )
        )
        return

    decoder = AnswerStreamDecoder()
    raw_chunks: list[str] = []
    for chunk in generator.generate_stream(SYSTEM_PROMPT, build_user_message(query, hits)):
        raw_chunks.append(chunk)
        delta = decoder.feed(chunk)
        if delta:
            yield AnswerDeltaEvent(delta)

    result = _parse_raw("".join(raw_chunks), hits)

    answer = result.answer
    if decision.action == "advise" and not result.parse_failed:
        answer = result.answer + ADVICE_DISCLAIMER

    yield FinalEvent(
        replace(
            result,
            answer=answer,
            query_category=decision.category,
            category_confidence=decision.confidence,
            routing_action=decision.action,
        )
    )
