import pytest

from app.classifier.dataset import (
    CATEGORIES,
    DatasetError,
    LabeledQuery,
    dedupe,
    label_counts,
    load_dataset,
    normalize_query,
    parse_generation_batch,
    save_dataset,
)


def test_categories_are_the_agreed_four() -> None:
    assert CATEGORIES == ("factual", "procedural", "advice_seeking", "out_of_scope")


def test_normalize_query_collapses_case_punctuation_whitespace() -> None:
    a = normalize_query("How do I apply for OPT?")
    b = normalize_query("  how do i   apply for opt ")
    assert a == b == "how do i apply for opt"


def test_dedupe_removes_near_duplicates() -> None:
    rows = [
        LabeledQuery("What is an EAD?", "factual"),
        LabeledQuery("what is an ead", "factual"),
        LabeledQuery("What is SEVIS?", "factual"),
    ]
    result = dedupe(rows)
    assert [r.query for r in result] == ["What is an EAD?", "What is SEVIS?"]


def test_dedupe_respects_existing_rows() -> None:
    existing = [LabeledQuery("What is an EAD?", "factual")]
    rows = [
        LabeledQuery("WHAT IS AN EAD", "factual"),
        LabeledQuery("What is Form I-983?", "factual"),
    ]
    result = dedupe(rows, existing=existing)
    assert [r.query for r in result] == ["What is Form I-983?"]


def test_parse_generation_batch_happy_path() -> None:
    raw = '{"queries": ["How long is OPT?", "What is cap gap?"]}'
    rows = parse_generation_batch(raw, "factual")
    assert len(rows) == 2
    assert all(r.label == "factual" for r in rows)


def test_parse_generation_batch_handles_fences_and_prose() -> None:
    raw = 'Here you go:\n```json\n{"queries": ["how do i file i-765"]}\n```'
    rows = parse_generation_batch(raw, "procedural")
    assert rows[0].query == "how do i file i-765"


def test_parse_generation_batch_skips_non_string_items() -> None:
    raw = '{"queries": ["valid query", 42, "", null, "another valid"]}'
    rows = parse_generation_batch(raw, "out_of_scope")
    assert [r.query for r in rows] == ["valid query", "another valid"]


def test_parse_generation_batch_rejects_missing_queries_key() -> None:
    with pytest.raises(DatasetError):
        parse_generation_batch('{"items": ["x"]}', "factual")


def test_parse_generation_batch_rejects_empty_batch() -> None:
    with pytest.raises(DatasetError):
        parse_generation_batch('{"queries": []}', "factual")


def test_parse_generation_batch_rejects_invalid_label() -> None:
    with pytest.raises(DatasetError):
        parse_generation_batch('{"queries": ["x"]}', "not_a_label")


def test_load_dataset_roundtrip(tmp_path) -> None:
    rows = [
        LabeledQuery("How long is OPT?", "factual"),
        LabeledQuery("should i apply early", "advice_seeking"),
    ]
    path = tmp_path / "data.jsonl"
    save_dataset(rows, path)
    loaded = load_dataset(path)
    assert loaded == rows


def test_load_dataset_rejects_bad_label(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"query": "hello", "label": "banana"}\n')
    with pytest.raises(DatasetError) as exc_info:
        load_dataset(path)
    assert "Line 1" in str(exc_info.value)


def test_load_dataset_rejects_empty_query(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"query": "  ", "label": "factual"}\n')
    with pytest.raises(DatasetError):
        load_dataset(path)


def test_load_dataset_rejects_invalid_json(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"query": "hello", "label": "factual"\n')
    with pytest.raises(DatasetError):
        load_dataset(path)


def test_load_dataset_skips_blank_lines(tmp_path) -> None:
    path = tmp_path / "data.jsonl"
    path.write_text('{"query": "a", "label": "factual"}\n\n{"query": "b", "label": "procedural"}\n')
    assert len(load_dataset(path)) == 2


def test_label_counts_covers_all_categories() -> None:
    rows = [LabeledQuery("x", "factual"), LabeledQuery("y", "factual")]
    counts = label_counts(rows)
    assert counts["factual"] == 2
    assert counts["out_of_scope"] == 0
    assert set(counts) == set(CATEGORIES)


def test_seed_file_is_valid() -> None:
    from pathlib import Path

    seed_path = Path(__file__).resolve().parents[2] / "data" / "classifier" / "seed_queries.jsonl"
    rows = load_dataset(seed_path)
    assert len(rows) >= 100
    counts = label_counts(rows)
    assert all(count >= 20 for count in counts.values())
    assert len(dedupe(rows)) == len(rows)
