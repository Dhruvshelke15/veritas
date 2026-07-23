from pathlib import Path

from app.eval import storage
from app.eval.storage import QuestionResultRow


def make_row(question_id: str = "q1") -> QuestionResultRow:
    return QuestionResultRow(
        question_id=question_id,
        query="How many days?",
        category="factual",
        retrieval_hit=True,
        faithfulness_score=5,
        faithfulness_rationale="Fully grounded.",
        classifier_predicted="factual",
        classifier_correct=True,
        sufficient_context=True,
        routing_action="standard",
        answer="90 days.",
    )


def test_creates_tables_and_db_file(tmp_path: Path) -> None:
    db_path = tmp_path / "sub" / "eval.db"
    conn = storage.connect(db_path)
    assert db_path.exists()
    conn.close()


def test_run_and_question_result_round_trip(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    run_id = storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    storage.save_question_result(conn, run_id, make_row())
    storage.finalize_run(conn, run_id, 0.9, 4.5, {"factual": 1.0})

    run_row = conn.execute(
        "SELECT retrieval_hit_rate, mean_faithfulness, classifier_accuracy_json FROM eval_runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    assert run_row[0] == 0.9
    assert run_row[1] == 4.5
    assert run_row[2] == '{"factual": 1.0}'

    question_row = conn.execute(
        "SELECT question_id, retrieval_hit, faithfulness_score, sufficient_context "
        "FROM eval_question_results WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    assert question_row[0] == "q1"
    assert question_row[1] == 1
    assert question_row[2] == 5
    assert question_row[3] == 1


def test_none_values_persist_as_null(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    run_id = storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    row = QuestionResultRow(
        question_id="q2",
        query="What is the capital of France?",
        category="out_of_scope",
        retrieval_hit=None,
        faithfulness_score=None,
        faithfulness_rationale="judge error: unparseable",
        classifier_predicted=None,
        classifier_correct=None,
        sufficient_context=False,
        routing_action="reject",
        answer="Out of scope.",
    )
    storage.save_question_result(conn, run_id, row)

    result = conn.execute(
        "SELECT retrieval_hit, faithfulness_score, classifier_predicted, classifier_correct "
        "FROM eval_question_results WHERE question_id = 'q2'"
    ).fetchone()
    assert result == (None, None, None, None)


def test_multiple_runs_are_independent(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    run_1 = storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    run_2 = storage.create_run(conn, "2026-07-22T01:00:00+00:00")
    assert run_1 != run_2

    storage.save_question_result(conn, run_1, make_row("q1"))
    storage.save_question_result(conn, run_2, make_row("q1"))

    count = conn.execute("SELECT COUNT(*) FROM eval_question_results").fetchone()[0]
    assert count == 2


def test_list_runs_returns_newest_first_with_parsed_accuracy(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    run_1 = storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    run_2 = storage.create_run(conn, "2026-07-22T01:00:00+00:00")
    storage.finalize_run(conn, run_1, 0.8, 4.0, {"factual": 1.0})
    storage.finalize_run(conn, run_2, 0.9, 4.5, {"factual": 0.5})

    runs = storage.list_runs(conn)

    assert [r["run_id"] for r in runs] == [run_2, run_1]
    assert runs[0]["classifier_accuracy"] == {"factual": 0.5}
    assert runs[1]["retrieval_hit_rate"] == 0.8


def test_list_runs_handles_null_classifier_accuracy(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    run_id = storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    storage.finalize_run(conn, run_id, 1.0, 5.0, None)

    runs = storage.list_runs(conn)
    assert runs[0]["classifier_accuracy"] is None


def test_get_run_detail_returns_run_and_questions(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    run_id = storage.create_run(conn, "2026-07-22T00:00:00+00:00")
    storage.save_question_result(conn, run_id, make_row("q1"))
    storage.finalize_run(conn, run_id, 1.0, 5.0, {"factual": 1.0})

    detail = storage.get_run_detail(conn, run_id)

    assert detail is not None
    assert detail["run"]["run_id"] == run_id
    assert len(detail["questions"]) == 1
    assert detail["questions"][0]["question_id"] == "q1"
    assert detail["questions"][0]["retrieval_hit"] is True
    assert detail["questions"][0]["sufficient_context"] is True


def test_get_run_detail_returns_none_for_missing_run(tmp_path: Path) -> None:
    conn = storage.connect(tmp_path / "eval.db")
    assert storage.get_run_detail(conn, 999) is None
