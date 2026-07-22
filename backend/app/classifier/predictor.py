from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.classifier.dataset import CATEGORIES
from app.config import settings


@dataclass(frozen=True)
class Classification:
    label: str
    confidence: float
    probabilities: dict[str, float]


class QueryClassifier:
    def __init__(self, model_path: Path) -> None:
        from app.classifier.model import load_model

        self._model = load_model(model_path)

    def classify(self, query: str) -> Classification:
        import tensorflow as tf

        probs = self._model.predict(tf.constant([query]), verbose=0)[0]
        probabilities = {CATEGORIES[i]: float(probs[i]) for i in range(len(CATEGORIES))}
        best_index = int(probs.argmax())
        return Classification(
            label=CATEGORIES[best_index],
            confidence=float(probs[best_index]),
            probabilities=probabilities,
        )


@lru_cache(maxsize=1)
def get_classifier() -> QueryClassifier | None:
    model_path = settings.classifier_model_path
    if not model_path.exists():
        return None
    return QueryClassifier(model_path)
