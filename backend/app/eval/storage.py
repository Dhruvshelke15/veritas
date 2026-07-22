import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    retrieval_hit_rate REAL,
    mean_faithfulness REAL,
    classifier_accuracy_json TEXT
);

CREATE TABLE IF NOT EXISTS eval_question_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES eval_runs(run_id),
    question_id TEXT NOT NULL,
    query TEXT NOT NULL,
    category TEXT NOT NULL,
    retrieval_hit INTEGER,
    faithfulness_score INTEGER,
    faithfulness_rationale TEXT,
    classifier_predicted TEXT,
    classifier_correct INTEGER,
    sufficient_context INTEGER NOT NULL,
    routing_action TEXT NOT NULL,
    answer TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class QuestionResultRow:
    question_id: str
    query: str
    category: str
    retrieval_hit: bool | None
    faithfulness_score: int | None
    faithfulness_rationale: str | None
    classifier_predicted: str | None
    classifier_correct: bool | None
    sufficient_context: bool
    routing_action: str
    answer: str


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def create_run(conn: sqlite3.Connection, started_at: str) -> int:
    cursor = conn.execute("INSERT INTO eval_runs (started_at) VALUES (?)", (started_at,))
    conn.commit()
    run_id = cursor.lastrowid
    assert run_id is not None
    return run_id


def save_question_result(conn: sqlite3.Connection, run_id: int, row: QuestionResultRow) -> None:
    conn.execute(
        """
        INSERT INTO eval_question_results (
            run_id, question_id, query, category, retrieval_hit,
            faithfulness_score, faithfulness_rationale,
            classifier_predicted, classifier_correct,
            sufficient_context, routing_action, answer
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            row.question_id,
            row.query,
            row.category,
            _to_int_or_none(row.retrieval_hit),
            row.faithfulness_score,
            row.faithfulness_rationale,
            row.classifier_predicted,
            _to_int_or_none(row.classifier_correct),
            int(row.sufficient_context),
            row.routing_action,
            row.answer,
        ),
    )
    conn.commit()


def finalize_run(
    conn: sqlite3.Connection,
    run_id: int,
    retrieval_hit_rate: float | None,
    mean_faithfulness: float | None,
    classifier_accuracy: dict[str, float] | None,
) -> None:
    conn.execute(
        """
        UPDATE eval_runs
        SET retrieval_hit_rate = ?, mean_faithfulness = ?, classifier_accuracy_json = ?
        WHERE run_id = ?
        """,
        (
            retrieval_hit_rate,
            mean_faithfulness,
            json.dumps(classifier_accuracy) if classifier_accuracy is not None else None,
            run_id,
        ),
    )
    conn.commit()


def _to_int_or_none(value: bool | None) -> int | None:
    return None if value is None else int(value)
