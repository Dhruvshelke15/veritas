from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from app.classifier.predictor import Classification
from app.eval.golden import GoldenQuestion


class Classifier(Protocol):
    def classify(self, query: str) -> Classification: ...


@dataclass(frozen=True)
class ClassifierEvalResult:
    question_id: str
    expected: str
    predicted: str
    confidence: float
    correct: bool


def evaluate_classifier(
    classifier: Classifier, questions: list[GoldenQuestion]
) -> list[ClassifierEvalResult]:
    results: list[ClassifierEvalResult] = []
    for question in questions:
        classification = classifier.classify(question.query)
        results.append(
            ClassifierEvalResult(
                question_id=question.id,
                expected=question.category,
                predicted=classification.label,
                confidence=classification.confidence,
                correct=classification.label == question.category,
            )
        )
    return results


def per_category_accuracy(results: list[ClassifierEvalResult]) -> dict[str, float]:
    totals: dict[str, int] = defaultdict(int)
    correct: dict[str, int] = defaultdict(int)
    for result in results:
        totals[result.expected] += 1
        if result.correct:
            correct[result.expected] += 1
    return {category: correct[category] / totals[category] for category in totals}
