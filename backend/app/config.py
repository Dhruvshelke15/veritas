from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(BACKEND_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VERITAS_", env_file=".env", extra="ignore")

    upload_dir: Path = REPO_ROOT / "data" / "uploads"
    chroma_dir: Path = REPO_ROOT / "data" / "chroma"
    collection_name: str = "veritas"

    embedding_model: str = "all-MiniLM-L6-v2"

    chunk_size: int = 800
    chunk_overlap: int = 150

    default_top_k: int = 4

    anthropic_model: str = "claude-haiku-4-5-20251001"
    anthropic_max_tokens: int = 1024

    classifier_model_path: Path = REPO_ROOT / "data" / "classifier" / "model.keras"
    classifier_reject_threshold: float = 0.7
    # TensorFlow + PyTorch (via sentence-transformers) both resident at once
    # is enough to OOM a memory-constrained deployment. Routing already fails
    # open when there's no classifier (see app/rag/routing.py: route(None)
    # -> "standard"), so this is a safe memory-pressure release valve — it
    # costs the out-of-scope pre-filter and the advice-seeking disclaimer,
    # not the citation-validation refusal backstop.
    classifier_enabled: bool = True

    golden_set_path: Path = REPO_ROOT / "data" / "eval" / "golden_set.jsonl"
    eval_db_path: Path = REPO_ROOT / "data" / "eval" / "eval_results.db"

    allowed_extensions: frozenset[str] = frozenset({".pdf", ".md", ".txt"})

    # Comma-separated list of allowed frontend origins for CORS. Defaults to
    # the Vite dev server; set to the deployed frontend's URL in production.
    allowed_origins: str = "http://localhost:5173"


settings = Settings()
