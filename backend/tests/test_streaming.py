import json

from app.classifier.predictor import Classification
from app.ingestion.indexer import SearchHit
from app.rag.streaming import (
    AnswerDeltaEvent,
    AnswerStreamDecoder,
    FinalEvent,
    MetaEvent,
    ask_routed_stream,
)


class FakeStreamingGenerator:
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.calls = 0

    def generate_stream(self, system: str, user_message: str):
        self.calls += 1
        yield from self.chunks


class FakeRetriever:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls = 0

    def __call__(self, query: str, top_k: int) -> list[SearchHit]:
        self.calls += 1
        return self.hits


def make_classification(label: str, confidence: float) -> Classification:
    probs = {c: 0.0 for c in ("factual", "procedural", "advice_seeking", "out_of_scope")}
    probs[label] = confidence
    return Classification(label=label, confidence=confidence, probabilities=probs)


def make_hit() -> SearchHit:
    return SearchHit(
        chunk_id="doc1:0",
        text="An F-1 student may not accrue more than 90 days of unemployment.",
        distance=0.3,
        metadata={"source_file": "policy.md", "doc_id": "doc1", "chunk_index": 0},
    )


def chunk_string(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


# --- AnswerStreamDecoder ---


def test_decoder_emits_plain_text_incrementally() -> None:
    decoder = AnswerStreamDecoder()
    raw = json.dumps({"answer": "The limit is 90 days.", "citations": [], "sufficient_context": True})
    emitted = ""
    for chunk in chunk_string(raw, 5):
        emitted += decoder.feed(chunk)
    assert emitted == "The limit is 90 days."


def test_decoder_handles_split_escape_sequence() -> None:
    decoder = AnswerStreamDecoder()
    raw = json.dumps({"answer": 'Line one\nLine "two"', "citations": [], "sufficient_context": True})
    # Split at a point that lands mid-escape-sequence somewhere in the string.
    emitted = ""
    for i in range(len(raw)):
        emitted += decoder.feed(raw[i])
    assert emitted == 'Line one\nLine "two"'


def test_decoder_handles_unicode_escape() -> None:
    decoder = AnswerStreamDecoder()
    raw = '{"answer": "caf\\u00e9", "citations": [], "sufficient_context": true}'
    emitted = ""
    for chunk in chunk_string(raw, 3):
        emitted += decoder.feed(chunk)
    assert emitted == "café"


def test_decoder_skips_fenced_prefix() -> None:
    decoder = AnswerStreamDecoder()
    inner = json.dumps({"answer": "24 months.", "citations": [], "sufficient_context": True})
    raw = f"```json\n{inner}\n```"
    emitted = "".join(decoder.feed(c) for c in chunk_string(raw, 4))
    assert emitted == "24 months."


def test_decoder_emits_nothing_before_answer_key_found() -> None:
    decoder = AnswerStreamDecoder()
    assert decoder.feed('{"citat') == ""
    assert decoder.feed('ions": [') == ""


def test_decoder_stops_emitting_after_closing_quote() -> None:
    decoder = AnswerStreamDecoder()
    decoder.feed('{"answer": "done"')
    assert decoder.feed(', "citations": ["ignored answer: fake"]}') == ""


# --- ask_routed_stream ---


def test_standard_path_yields_meta_then_deltas_then_final() -> None:
    response = json.dumps(
        {"answer": "The limit is 90 days.", "citations": ["doc1:0"], "sufficient_context": True}
    )
    generator = FakeStreamingGenerator(chunk_string(response, 6))
    retriever = FakeRetriever([make_hit()])

    events = list(
        ask_routed_stream(
            "how many days", generator, make_classification("factual", 0.9), retriever=retriever
        )
    )

    assert isinstance(events[0], MetaEvent)
    assert events[0].routing_action == "standard"
    assert any(isinstance(e, AnswerDeltaEvent) for e in events)
    deltas = "".join(e.text for e in events if isinstance(e, AnswerDeltaEvent))
    assert deltas == "The limit is 90 days."

    final = events[-1]
    assert isinstance(final, FinalEvent)
    assert final.result.answer == "The limit is 90 days."
    assert final.result.citations[0].chunk_id == "doc1:0"
    assert final.result.routing_action == "standard"


def test_reject_path_skips_retrieval_and_generation() -> None:
    generator = FakeStreamingGenerator(["should never be consumed"])
    retriever = FakeRetriever([make_hit()])

    events = list(
        ask_routed_stream(
            "capital of france",
            generator,
            make_classification("out_of_scope", 0.95),
            retriever=retriever,
        )
    )

    assert len(events) == 2
    assert isinstance(events[0], MetaEvent)
    assert events[0].routing_action == "reject"
    assert isinstance(events[1], FinalEvent)
    assert events[1].result.sufficient_context is False
    assert retriever.calls == 0
    assert generator.calls == 0


def test_advice_disclaimer_appended_only_in_final_event() -> None:
    response = json.dumps(
        {"answer": "The limit is 90 days.", "citations": ["doc1:0"], "sufficient_context": True}
    )
    generator = FakeStreamingGenerator([response])
    retriever = FakeRetriever([make_hit()])

    events = list(
        ask_routed_stream(
            "should i worry",
            generator,
            make_classification("advice_seeking", 0.8),
            retriever=retriever,
        )
    )

    deltas = "".join(e.text for e in events if isinstance(e, AnswerDeltaEvent))
    assert "Note:" not in deltas

    final = events[-1]
    assert isinstance(final, FinalEvent)
    assert final.result.answer.startswith("The limit is 90 days.")
    assert "Note:" in final.result.answer


def test_empty_hits_short_circuits_without_generation() -> None:
    generator = FakeStreamingGenerator(["should never be consumed"])
    retriever = FakeRetriever([])

    events = list(
        ask_routed_stream("anything", generator, None, retriever=retriever)
    )

    assert len(events) == 2
    assert isinstance(events[1], FinalEvent)
    assert generator.calls == 0


def test_parse_failure_downgrades_final_result() -> None:
    generator = FakeStreamingGenerator(["not json at all"])
    retriever = FakeRetriever([make_hit()])

    events = list(
        ask_routed_stream("how many days", generator, None, retriever=retriever)
    )

    final = events[-1]
    assert isinstance(final, FinalEvent)
    assert final.result.parse_failed is True
    assert final.result.sufficient_context is False
