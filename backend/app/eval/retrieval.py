from app.eval.golden import GoldenQuestion
from app.ingestion.indexer import SearchHit


def retrieval_hit(question: GoldenQuestion, hits: list[SearchHit]) -> bool | None:
    """Did any retrieved chunk come from a source the question expects?

    Returns None when the question has no expected source (e.g. refusal
    cases for out-of-corpus topics) -- there is nothing to hit, so the
    question is excluded from the hit-rate aggregate rather than counted
    as a miss.
    """
    if not question.expected_source_files:
        return None
    hit_sources = {str(hit.metadata.get("source_file")) for hit in hits}
    return bool(hit_sources & set(question.expected_source_files))


def hit_rate(results: list[bool | None]) -> float | None:
    applicable = [r for r in results if r is not None]
    if not applicable:
        return None
    return sum(applicable) / len(applicable)
