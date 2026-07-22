import json
from dataclasses import dataclass
from pathlib import Path

from app.classifier.dataset import CATEGORIES


class GoldenSetError(ValueError):
    pass


@dataclass(frozen=True)
class GoldenQuestion:
    id: str
    query: str
    category: str
    expect_refusal: bool
    expected_source_files: list[str]
    reference_answer: str


def load_golden_set(path: Path) -> list[GoldenQuestion]:
    rows: list[GoldenQuestion] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoldenSetError(f"Line {line_number}: invalid JSON: {exc}") from exc

        qid = data.get("id")
        query = data.get("query")
        category = data.get("category")
        expected_source_files = data.get("expected_source_files")
        reference_answer = data.get("reference_answer")

        if not isinstance(qid, str) or not qid.strip():
            raise GoldenSetError(f"Line {line_number}: missing or empty 'id'")
        if qid in seen_ids:
            raise GoldenSetError(f"Line {line_number}: duplicate id {qid!r}")
        if not isinstance(query, str) or not query.strip():
            raise GoldenSetError(f"Line {line_number}: missing or empty 'query'")
        if category not in CATEGORIES:
            raise GoldenSetError(f"Line {line_number}: invalid category {category!r}")
        if not isinstance(expected_source_files, list) or not all(
            isinstance(s, str) for s in expected_source_files
        ):
            raise GoldenSetError(f"Line {line_number}: 'expected_source_files' must be a list of strings")
        if not isinstance(reference_answer, str) or not reference_answer.strip():
            raise GoldenSetError(f"Line {line_number}: missing or empty 'reference_answer'")

        seen_ids.add(qid)
        rows.append(
            GoldenQuestion(
                id=qid,
                query=query.strip(),
                category=category,
                expect_refusal=bool(data.get("expect_refusal", False)),
                expected_source_files=expected_source_files,
                reference_answer=reference_answer.strip(),
            )
        )
    return rows
