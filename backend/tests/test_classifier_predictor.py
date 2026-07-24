import pytest

from app.classifier import predictor
from app.config import settings


@pytest.fixture(autouse=True)
def _clear_classifier_cache():
    predictor.get_classifier.cache_clear()
    yield
    predictor.get_classifier.cache_clear()


def test_get_classifier_returns_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "classifier_enabled", False)
    assert predictor.get_classifier() is None


def test_get_classifier_returns_none_when_model_file_missing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "classifier_enabled", True)
    monkeypatch.setattr(settings, "classifier_model_path", tmp_path / "does_not_exist.keras")
    assert predictor.get_classifier() is None
