from app.classifier.predictor import Classification
from app.eval.classifier_metrics import evaluate_classifier, per_category_accuracy
from app.eval.golden import GoldenQuestion


class FakeClassifier:
    def __init__(self, labels_by_query: dict[str, str]) -> None:
        self._labels = labels_by_query

    def classify(self, query: str) -> Classification:
        label = self._labels[query]
        return Classification(label=label, confidence=0.9, probabilities={label: 0.9})


def make_question(qid: str, query: str, category: str) -> GoldenQuestion:
    return GoldenQuestion(
        id=qid,
        query=query,
        category=category,
        expect_refusal=False,
        expected_source_files=[],
        reference_answer="ref",
    )


def test_evaluate_classifier_marks_correct_and_incorrect() -> None:
    questions = [
        make_question("q1", "How many days?", "factual"),
        make_question("q2", "How do I apply?", "procedural"),
    ]
    classifier = FakeClassifier({"How many days?": "factual", "How do I apply?": "advice_seeking"})
    results = evaluate_classifier(classifier, questions)
    assert results[0].correct is True
    assert results[1].correct is False
    assert results[1].predicted == "advice_seeking"


def test_per_category_accuracy_computes_ratio_per_expected_category() -> None:
    questions = [
        make_question("q1", "Q1", "factual"),
        make_question("q2", "Q2", "factual"),
        make_question("q3", "Q3", "procedural"),
    ]
    classifier = FakeClassifier({"Q1": "factual", "Q2": "advice_seeking", "Q3": "procedural"})
    results = evaluate_classifier(classifier, questions)
    accuracy = per_category_accuracy(results)
    assert accuracy["factual"] == 0.5
    assert accuracy["procedural"] == 1.0
