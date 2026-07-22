import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.rag.parsing import AnswerParseError, extract_json_payload

CATEGORIES: tuple[str, ...] = ("factual", "procedural", "advice_seeking", "out_of_scope")

WHITESPACE_PATTERN = re.compile(r"\s+")
PUNCT_PATTERN = re.compile(r"[^\w\s]")


class DatasetError(ValueError):
    pass


@dataclass(frozen=True)
class LabeledQuery:
    query: str
    label: str


def normalize_query(query: str) -> str:
    text = query.strip().lower()
    text = PUNCT_PATTERN.sub("", text)
    return WHITESPACE_PATTERN.sub(" ", text)


def load_dataset(path: Path) -> list[LabeledQuery]:
    rows: list[LabeledQuery] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"Line {line_number}: invalid JSON: {exc}") from exc
        query = data.get("query")
        label = data.get("label")
        if not isinstance(query, str) or not query.strip():
            raise DatasetError(f"Line {line_number}: missing or empty 'query'")
        if label not in CATEGORIES:
            raise DatasetError(f"Line {line_number}: invalid label {label!r}")
        rows.append(LabeledQuery(query=query.strip(), label=label))
    return rows


def save_dataset(rows: list[LabeledQuery], path: Path) -> None:
    lines = [json.dumps({"query": r.query, "label": r.label}) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dedupe(rows: list[LabeledQuery], existing: list[LabeledQuery] | None = None) -> list[LabeledQuery]:
    seen = {normalize_query(r.query) for r in existing or []}
    result: list[LabeledQuery] = []
    for row in rows:
        key = normalize_query(row.query)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def parse_generation_batch(raw: str, expected_label: str) -> list[LabeledQuery]:
    if expected_label not in CATEGORIES:
        raise DatasetError(f"Invalid label {expected_label!r}")
    try:
        payload = extract_json_payload(raw)
        data = json.loads(payload)
    except (AnswerParseError, json.JSONDecodeError) as exc:
        raise DatasetError(f"Unparseable generation batch: {exc}") from exc

    queries = data.get("queries")
    if not isinstance(queries, list):
        raise DatasetError("Generation batch missing 'queries' list")

    rows: list[LabeledQuery] = []
    for item in queries:
        if isinstance(item, str) and item.strip():
            rows.append(LabeledQuery(query=item.strip(), label=expected_label))
    if not rows:
        raise DatasetError("Generation batch contained no usable queries")
    return rows


def label_counts(rows: list[LabeledQuery]) -> dict[str, int]:
    counts = {category: 0 for category in CATEGORIES}
    for row in rows:
        counts[row.label] += 1
    return counts
