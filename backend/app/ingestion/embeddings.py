import os
import time
from typing import Any

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings, Space
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

_RATE_LIMIT_RETRY_DELAYS_SECONDS = (1.0, 2.0, 4.0)


class HFInferenceEmbeddingFunction(EmbeddingFunction[Documents]):
    """Embeds text via HuggingFace's Inference Providers router.

    chromadb's own HuggingFaceEmbeddingFunction posts directly to
    api-inference.huggingface.co, which HF has decommissioned — that
    domain no longer resolves at all (DNS failure, confirmed against two
    independent networks), not just returning an auth/404 error. HF's
    current routing goes through router.huggingface.co under a multi-
    provider "Inference Providers" system instead. Rather than hardcode
    that URL ourselves and risk it drifting again, this delegates to
    huggingface_hub's InferenceClient, which HF's own SDK keeps in sync
    with whatever the current routing actually is.
    """

    def __init__(self, model_name: str, provider: str = "hf-inference", timeout: float = 45.0) -> None:
        api_key = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("CHROMA_HUGGINGFACE_API_KEY")
        if not api_key:
            raise ValueError("The HUGGINGFACE_API_KEY environment variable is not set.")

        self.model_name = model_name
        self.provider = provider
        # InferenceClient's own default timeout is None, which its docstring
        # describes as "loop until the server is available" -- unbounded. A
        # transient "model loading" response from HF then hangs the request
        # forever instead of failing cleanly (observed: 2+ minutes with no
        # response). Bounded here so a slow cold start surfaces as a real,
        # catchable error instead of a silent hang.
        self._client = InferenceClient(model=model_name, provider=provider, token=api_key, timeout=timeout)

    def __call__(self, input: Documents) -> Embeddings:
        # huggingface_hub does a one-time model-metadata lookup (a separate
        # call from the actual embedding request, cached per-process
        # afterward) the first time this model+task pair is used. That
        # lookup has no built-in retry, and observed in production it gets
        # 429-rate-limited on a real fraction of cold starts -- not a rare
        # fluke, a recurring failure mode. Retried here with backoff since
        # a 429 is expected to be transient; anything else (auth, 5xx)
        # still raises immediately.
        for delay in (*_RATE_LIMIT_RETRY_DELAYS_SECONDS, None):
            try:
                vectors = self._client.feature_extraction(list(input))
                return [np.array(vector, dtype=np.float32) for vector in vectors]
            except HfHubHTTPError as exc:
                if exc.response.status_code != 429 or delay is None:
                    raise
                time.sleep(delay)
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def name() -> str:
        return "hf_inference_router"

    def default_space(self) -> Space:
        return "cosine"

    def supported_spaces(self) -> list[Space]:
        return ["cosine", "l2", "ip"]

    def get_config(self) -> dict[str, Any]:
        return {"model_name": self.model_name, "provider": self.provider}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "HFInferenceEmbeddingFunction":
        return HFInferenceEmbeddingFunction(
            model_name=config["model_name"], provider=config.get("provider", "hf-inference")
        )

    def validate_config_update(self, old_config: dict[str, Any], new_config: dict[str, Any]) -> None:
        return
