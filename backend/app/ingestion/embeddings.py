import os
from typing import Any

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings, Space
from huggingface_hub import InferenceClient


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

    def __init__(self, model_name: str, provider: str = "hf-inference") -> None:
        api_key = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("CHROMA_HUGGINGFACE_API_KEY")
        if not api_key:
            raise ValueError("The HUGGINGFACE_API_KEY environment variable is not set.")

        self.model_name = model_name
        self.provider = provider
        self._client = InferenceClient(model=model_name, provider=provider, token=api_key)

    def __call__(self, input: Documents) -> Embeddings:
        vectors = self._client.feature_extraction(list(input))
        return [np.array(vector, dtype=np.float32) for vector in vectors]

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
