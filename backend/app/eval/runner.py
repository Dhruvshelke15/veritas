from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.eval import storage
from app.eval.classifier_metrics import Classifier
from app.eval.faithfulness import FaithfulnessJudgeError, judge_faithfulness
from app.eval.golden import GoldenQuestion
from app.eval.retrieval import hit_rate as aggregate_hit_rate
from app.eval.retrieval import retrieval_hit
from app.eval.storage import QuestionResultRow
from app.ingestion.indexer import similarity_search
from app.rag.generator import Generator
from app.rag.pipeline import ask_routed


@dataclass(frozen=True)
class EvalReport:
    run_id: int
    retrieval_hit_rate: float | None
    mean_faithfulness: float | None
    classifier_accuracy: dict[str, float] | None


def run_eval(
    questions: list[GoldenQuestion],
    generator: Generator,
    judge_generator: Generator,
    classifier: Classifier | None,
    top_k: int,
    db_path: Path,
) -> EvalReport:
    conn = storage.connect(db_path)
    run_id = storage.create_run(conn, datetime.now(UTC).isoformat())

    retrieval_results: list[bool | None] = []
    faithfulness_scores: list[int] = []
    classifier_correct_by_category: dict[str, list[bool]] = {}

    for question in questions:
        hits = similarity_search(question.query, top_k=top_k)
        hit = retrieval_hit(question, hits)
        retrieval_results.append(hit)

        classification = classifier.classify(question.query) if classifier is not None else None

        result = ask_routed(
            question.query,
            generator=generator,
            classification=classification,
            top_k=top_k,
            retriever=lambda _q, _k, _hits=hits: _hits,
        )

        try:
            faithfulness = judge_faithfulness(question, result, judge_generator)
            faithfulness_scores.append(faithfulness.score)
            score, rationale = faithfulness.score, faithfulness.rationale
        except FaithfulnessJudgeError as exc:
            score, rationale = None, f"judge error: {exc}"

        classifier_correct = None
        if classification is not None:
            classifier_correct = classification.label == question.category
            classifier_correct_by_category.setdefault(question.category, []).append(classifier_correct)

        storage.save_question_result(
            conn,
            run_id,
            QuestionResultRow(
                question_id=question.id,
                query=question.query,
                category=question.category,
                retrieval_hit=hit,
                faithfulness_score=score,
                faithfulness_rationale=rationale,
                classifier_predicted=classification.label if classification is not None else None,
                classifier_correct=classifier_correct,
                sufficient_context=result.sufficient_context,
                routing_action=result.routing_action,
                answer=result.answer,
            ),
        )

    retrieval_hit_rate = aggregate_hit_rate(retrieval_results)
    mean_faithfulness = (
        sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else None
    )
    classifier_accuracy = (
        {
            category: sum(results) / len(results)
            for category, results in classifier_correct_by_category.items()
        }
        if classifier_correct_by_category
        else None
    )

    storage.finalize_run(conn, run_id, retrieval_hit_rate, mean_faithfulness, classifier_accuracy)

    return EvalReport(
        run_id=run_id,
        retrieval_hit_rate=retrieval_hit_rate,
        mean_faithfulness=mean_faithfulness,
        classifier_accuracy=classifier_accuracy,
    )
