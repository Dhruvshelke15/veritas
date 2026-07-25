import httpx
import numpy as np
import pytest
from huggingface_hub.errors import HfHubHTTPError

from app.ingestion.embeddings import HFInferenceEmbeddingFunction


@pytest.fixture(autouse=True)
def _fake_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "fake-token-for-tests")


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ingestion.embeddings.time.sleep", lambda _seconds: None)


def _rate_limit_error() -> HfHubHTTPError:
    request = httpx.Request("POST", "https://router.huggingface.co/hf-inference/x")
    response = httpx.Response(429, request=request)
    return HfHubHTTPError("rate limited", response=response)


def _server_error() -> HfHubHTTPError:
    request = httpx.Request("POST", "https://router.huggingface.co/hf-inference/x")
    response = httpx.Response(500, request=request)
    return HfHubHTTPError("server error", response=response)


def test_retries_on_429_and_eventually_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def flaky_feature_extraction(self, texts):
        calls["count"] += 1
        if calls["count"] < 3:
            raise _rate_limit_error()
        return np.array([[1.0, 2.0]] * len(texts), dtype=np.float32)

    monkeypatch.setattr("huggingface_hub.InferenceClient.feature_extraction", flaky_feature_extraction)

    fn = HFInferenceEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
    result = fn(["hello", "world"])

    assert calls["count"] == 3
    assert len(result) == 2
    assert list(result[0]) == [1.0, 2.0]


def test_gives_up_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def always_rate_limited(self, texts):
        calls["count"] += 1
        raise _rate_limit_error()

    monkeypatch.setattr("huggingface_hub.InferenceClient.feature_extraction", always_rate_limited)

    fn = HFInferenceEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
    with pytest.raises(HfHubHTTPError):
        fn(["hello"])

    assert calls["count"] == 4  # initial attempt + 3 retries


def test_non_429_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def server_error(self, texts):
        calls["count"] += 1
        raise _server_error()

    monkeypatch.setattr("huggingface_hub.InferenceClient.feature_extraction", server_error)

    fn = HFInferenceEmbeddingFunction(model_name="sentence-transformers/all-MiniLM-L6-v2")
    with pytest.raises(HfHubHTTPError):
        fn(["hello"])

    assert calls["count"] == 1
