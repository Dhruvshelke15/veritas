import pytest


@pytest.fixture(autouse=True)
def _default_huggingface_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # chromadb's HuggingFaceEmbeddingFunction raises ValueError at
    # construction time if no key is present in the environment, even if a
    # test never makes a real HTTP call. Individual tests that want to
    # exercise the "missing key" error path can still monkeypatch.delenv()
    # this within their own test.
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "fake-token-for-tests")
