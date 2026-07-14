import json

from app.ingestion.indexer import SearchHit
from app.rag.pipeline import (
    NO_RESULTS_ANSWER,
    PARSE_FAILURE_ANSWER,
    ask_with_hits,
)
from app.rag.prompt import SYSTEM_PROMPT, build_user_message


class FakeGenerator:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, user_message: str) -> str:
        self.calls.append((system, user_message))
        return self.response


def make_hits() -> list[SearchHit]:
    return [
        SearchHit(
            chunk_id="doc1:0",
            text="A Pod is the smallest deployable unit in Kubernetes.",
            distance=0.3,
            metadata={"source_file": "k8s.md", "doc_id": "doc1", "chunk_index": 0},
        ),
        SearchHit(
            chunk_id="doc1:1",
            text="Deployments provide declarative updates for Pods.",
            distance=0.5,
            metadata={"source_file": "k8s.md", "doc_id": "doc1", "chunk_index": 1, "page": 2},
        ),
    ]


def test_happy_path_returns_answer_with_resolved_citations() -> None:
    response = json.dumps(
        {
            "answer": "A Pod is the smallest deployable unit.",
            "citations": ["doc1:0"],
            "sufficient_context": True,
        }
    )
    result = ask_with_hits("What is a Pod?", make_hits(), FakeGenerator(response))
    assert result.sufficient_context is True
    assert result.parse_failed is False
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "doc1:0"
    assert result.citations[0].source_file == "k8s.md"
    assert result.citations[0].page is None


def test_citation_page_metadata_is_resolved() -> None:
    response = json.dumps(
        {"answer": "Deployments update Pods.", "citations": ["doc1:1"], "sufficient_context": True}
    )
    result = ask_with_hits("What do Deployments do?", make_hits(), FakeGenerator(response))
    assert result.citations[0].page == 2


def test_hallucinated_citations_are_filtered_and_reported() -> None:
    response = json.dumps(
        {
            "answer": "A Pod is the smallest unit.",
            "citations": ["doc1:0", "doc9:99"],
            "sufficient_context": True,
        }
    )
    result = ask_with_hits("What is a Pod?", make_hits(), FakeGenerator(response))
    assert [c.chunk_id for c in result.citations] == ["doc1:0"]
    assert result.hallucinated_citations == ["doc9:99"]


def test_sufficient_claim_with_zero_valid_citations_is_downgraded() -> None:
    response = json.dumps(
        {"answer": "Made up claim.", "citations": ["ghost:0"], "sufficient_context": True}
    )
    result = ask_with_hits("What is a Pod?", make_hits(), FakeGenerator(response))
    assert result.sufficient_context is False
    assert result.citations == []
    assert result.hallucinated_citations == ["ghost:0"]


def test_refusal_passes_through() -> None:
    response = json.dumps(
        {
            "answer": "The documents do not cover pricing.",
            "citations": [],
            "sufficient_context": False,
        }
    )
    result = ask_with_hits("What does it cost?", make_hits(), FakeGenerator(response))
    assert result.sufficient_context is False
    assert result.citations == []


def test_fenced_model_output_is_handled() -> None:
    inner = json.dumps(
        {"answer": "A Pod is the smallest unit.", "citations": ["doc1:0"], "sufficient_context": True}
    )
    result = ask_with_hits("What is a Pod?", make_hits(), FakeGenerator(f"```json\n{inner}\n```"))
    assert result.parse_failed is False
    assert result.citations[0].chunk_id == "doc1:0"


def test_unparseable_output_degrades_gracefully() -> None:
    result = ask_with_hits("What is a Pod?", make_hits(), FakeGenerator("Sorry, I refuse."))
    assert result.parse_failed is True
    assert result.answer == PARSE_FAILURE_ANSWER
    assert result.sufficient_context is False


def test_empty_retrieval_short_circuits_without_llm_call() -> None:
    generator = FakeGenerator("should never be called")
    result = ask_with_hits("Anything?", [], generator)
    assert result.answer == NO_RESULTS_ANSWER
    assert generator.calls == []


def test_prompt_contains_chunk_ids_and_query() -> None:
    hits = make_hits()
    message = build_user_message("What is a Pod?", hits)
    assert 'id="doc1:0"' in message
    assert 'id="doc1:1"' in message
    assert 'page=2' in message
    assert message.endswith("Question: What is a Pod?")
    assert "Never invent chunk IDs" in SYSTEM_PROMPT


def test_app_package_imports_cleanly() -> None:
    import app.main

    routes = {route.path for route in app.main.app.routes}
    assert {"/health", "/ingest", "/search", "/ask"} <= routes


def test_citation_carries_freshness_metadata() -> None:
    hit = SearchHit(
        chunk_id="doc2:0",
        text="STEM OPT extends post-completion OPT by 24 months.",
        distance=0.2,
        metadata={
            "source_file": "uscis_stem_opt_extension.md",
            "doc_id": "doc2",
            "chunk_index": 0,
            "source_url": "https://www.uscis.gov/example",
            "retrieved_date": "2026-07-14",
        },
    )
    response = json.dumps(
        {"answer": "24 months.", "citations": ["doc2:0"], "sufficient_context": True}
    )
    result = ask_with_hits("How long is STEM OPT?", [hit], FakeGenerator(response))
    assert result.citations[0].source_url == "https://www.uscis.gov/example"
    assert result.citations[0].retrieved_date == "2026-07-14"
