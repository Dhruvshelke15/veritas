from pathlib import Path

import pytest

from app.config import settings
from app.eval.golden import GoldenSetError, load_golden_set


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "golden.jsonl"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_valid_rows(tmp_path: Path) -> None:
    content = (
        '{"id": "a", "query": "How many days?", "category": "factual", '
        '"expect_refusal": false, "expected_source_files": ["doc.md"], '
        '"reference_answer": "90 days"}\n'
    )
    rows = load_golden_set(write(tmp_path, content))
    assert len(rows) == 1
    assert rows[0].id == "a"
    assert rows[0].expected_source_files == ["doc.md"]


def test_defaults_expect_refusal_to_false(tmp_path: Path) -> None:
    content = (
        '{"id": "a", "query": "Q", "category": "factual", '
        '"expected_source_files": [], "reference_answer": "R"}\n'
    )
    rows = load_golden_set(write(tmp_path, content))
    assert rows[0].expect_refusal is False


def test_rejects_duplicate_ids(tmp_path: Path) -> None:
    row = (
        '{"id": "a", "query": "Q", "category": "factual", '
        '"expected_source_files": [], "reference_answer": "R"}\n'
    )
    with pytest.raises(GoldenSetError, match="duplicate id"):
        load_golden_set(write(tmp_path, row + row))


def test_rejects_invalid_category(tmp_path: Path) -> None:
    content = (
        '{"id": "a", "query": "Q", "category": "not_a_category", '
        '"expected_source_files": [], "reference_answer": "R"}\n'
    )
    with pytest.raises(GoldenSetError, match="invalid category"):
        load_golden_set(write(tmp_path, content))


def test_rejects_missing_query(tmp_path: Path) -> None:
    content = (
        '{"id": "a", "category": "factual", '
        '"expected_source_files": [], "reference_answer": "R"}\n'
    )
    with pytest.raises(GoldenSetError, match="query"):
        load_golden_set(write(tmp_path, content))


def test_rejects_malformed_json(tmp_path: Path) -> None:
    with pytest.raises(GoldenSetError, match="invalid JSON"):
        load_golden_set(write(tmp_path, "{not json\n"))


def test_skips_blank_lines(tmp_path: Path) -> None:
    content = (
        '{"id": "a", "query": "Q", "category": "factual", '
        '"expected_source_files": [], "reference_answer": "R"}\n\n\n'
    )
    rows = load_golden_set(write(tmp_path, content))
    assert len(rows) == 1


def test_real_golden_set_loads_and_has_expected_size() -> None:
    rows = load_golden_set(settings.golden_set_path)
    assert 25 <= len(rows) <= 30
    categories = {row.category for row in rows}
    assert categories == {"factual", "procedural", "advice_seeking", "out_of_scope"}
    refusal_rows = [row for row in rows if row.expect_refusal]
    assert len(refusal_rows) >= 2
    assert all(row.expected_source_files == [] for row in refusal_rows)
