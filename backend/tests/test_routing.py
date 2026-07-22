import json

from app.classifier.predictor import Classification
from app.ingestion.indexer import SearchHit
from app.rag.pipeline import ask_routed
from app.rag.routing import ADVICE_DISCLAIMER, OUT_OF_SCOPE_ANSWER, route


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


def good_response() -> str:
    return json.dumps(
        {"answer": "The limit is 90 days.", "citations": ["doc1:0"], "sufficient_context": True}
    )


class FakeGenerator:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate(self, system: str, user_message: str) -> str:
        self.calls += 1
        return self.response


class FakeRetriever:
    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.calls = 0

    def __call__(self, query: str, top_k: int) -> list[SearchHit]:
        self.calls += 1
        return self.hits


def test_route_rejects_confident_out_of_scope() -> None:
    decision = route(make_classification("out_of_scope", 0.95))
    assert decision.action == "reject"


def test_route_fails_open_on_low_confidence_out_of_scope() -> None:
    decision = route(make_classification("out_of_scope", 0.55))
    assert decision.action == "standard"


def test_route_advises_on_advice_seeking() -> None:
    decision = route(make_classification("advice_seeking", 0.6))
    assert decision.action == "advise"


def test_route_standard_for_factual_and_procedural() -> None:
    assert route(make_classification("factual", 0.9)).action == "standard"
    assert route(make_classification("procedural", 0.9)).action == "standard"


def test_route_standard_when_classifier_missing() -> None:
    decision = route(None)
    assert decision.action == "standard"
    assert decision.category is None


def test_reject_skips_retrieval_and_generation() -> None:
    generator = FakeGenerator(good_response())
    retriever = FakeRetriever([make_hit()])
    result = ask_routed(
        "how do i get a green card",
        generator,
        make_classification("out_of_scope", 0.92),
        retriever=retriever,
    )
    assert result.routing_action == "reject"
    assert result.answer == OUT_OF_SCOPE_ANSWER
    assert result.sufficient_context is False
    assert retriever.calls == 0
    assert generator.calls == 0


def test_advice_appends_disclaimer() -> None:
    generator = FakeGenerator(good_response())
    result = ask_routed(
        "should i be worried about my unemployment days",
        generator,
        make_classification("advice_seeking", 0.8),
        retriever=FakeRetriever([make_hit()]),
    )
    assert result.routing_action == "advise"
    assert result.answer.endswith(ADVICE_DISCLAIMER)
    assert result.citations[0].chunk_id == "doc1:0"


def test_advice_disclaimer_skipped_on_parse_failure() -> None:
    generator = FakeGenerator("not json at all")
    result = ask_routed(
        "should i worry",
        generator,
        make_classification("advice_seeking", 0.8),
        retriever=FakeRetriever([make_hit()]),
    )
    assert result.parse_failed is True
    assert ADVICE_DISCLAIMER not in result.answer


def test_standard_path_carries_category_metadata() -> None:
    generator = FakeGenerator(good_response())
    result = ask_routed(
        "how many unemployment days on opt",
        generator,
        make_classification("factual", 0.88),
        retriever=FakeRetriever([make_hit()]),
    )
    assert result.routing_action == "standard"
    assert result.query_category == "factual"
    assert result.category_confidence == 0.88
    assert result.answer == "The limit is 90 days."


def test_unclassified_path_answers_normally() -> None:
    generator = FakeGenerator(good_response())
    result = ask_routed(
        "how many unemployment days on opt",
        generator,
        None,
        retriever=FakeRetriever([make_hit()]),
    )
    assert result.routing_action == "standard"
    assert result.query_category is None
    assert result.sufficient_context is True
