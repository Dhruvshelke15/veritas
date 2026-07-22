from dataclasses import dataclass, field, replace
from typing import Callable

from app.classifier.predictor import Classification
from app.config import settings
from app.ingestion.indexer import SearchHit, similarity_search
from app.rag.generator import Generator
from app.rag.parsing import AnswerParseError, parse_answer, validate_citations
from app.rag.prompt import SYSTEM_PROMPT, build_user_message
from app.rag.routing import ADVICE_DISCLAIMER, OUT_OF_SCOPE_ANSWER, RoutingDecision, route


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    text: str
    source_file: str
    page: int | None
    source_url: str | None
    retrieved_date: str | None


@dataclass(frozen=True)
class AskResult:
    answer: str
    citations: list[Citation]
    sufficient_context: bool
    hallucinated_citations: list[str] = field(default_factory=list)
    parse_failed: bool = False
    query_category: str | None = None
    category_confidence: float | None = None
    routing_action: str = "standard"

Retriever = Callable[[str, int], list[SearchHit]]


NO_RESULTS_ANSWER = "No documents have been ingested yet, or nothing relevant was found. Upload documents and try again."
PARSE_FAILURE_ANSWER = "The model returned an unparseable response. Please retry the question."


def to_citation(hit: SearchHit) -> Citation:
    page = hit.metadata.get("page")
    source_url = hit.metadata.get("source_url")
    retrieved_date = hit.metadata.get("retrieved_date")
    return Citation(
        chunk_id=hit.chunk_id,
        text=hit.text,
        source_file=str(hit.metadata.get("source_file", "unknown")),
        page=int(page) if page is not None else None,
        source_url=str(source_url) if source_url is not None else None,
        retrieved_date=str(retrieved_date) if retrieved_date is not None else None,
    )


def ask(query: str, generator: Generator, top_k: int | None = None) -> AskResult:
    hits = similarity_search(query, top_k=top_k or settings.default_top_k)
    return ask_with_hits(query, hits, generator)


def default_retriever(query: str, top_k: int) -> list[SearchHit]:
    return similarity_search(query, top_k=top_k)


def ask_routed(
    query: str,
    generator: Generator,
    classification: Classification | None,
    top_k: int | None = None,
    retriever: Retriever = default_retriever,
) -> AskResult:
    decision: RoutingDecision = route(classification)

    if decision.action == "reject":
        return AskResult(
            answer=OUT_OF_SCOPE_ANSWER,
            citations=[],
            sufficient_context=False,
            query_category=decision.category,
            category_confidence=decision.confidence,
            routing_action="reject",
        )

    hits = retriever(query, top_k or settings.default_top_k)
    result = ask_with_hits(query, hits, generator)

    answer = result.answer
    if decision.action == "advise" and not result.parse_failed:
        answer = result.answer + ADVICE_DISCLAIMER

    return replace(
        result,
        answer=answer,
        query_category=decision.category,
        category_confidence=decision.confidence,
        routing_action=decision.action,
    )


def ask_with_hits(query: str, hits: list[SearchHit], generator: Generator) -> AskResult:
    if not hits:
        return AskResult(answer=NO_RESULTS_ANSWER, citations=[], sufficient_context=False)

    raw = generator.generate(SYSTEM_PROMPT, build_user_message(query, hits))

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
