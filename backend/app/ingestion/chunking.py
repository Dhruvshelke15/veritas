import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_core.documents import Document

from app.config import settings

if TYPE_CHECKING:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: dict[str, str | int]


def compute_doc_id(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()[:12]


def build_splitter() -> "RecursiveCharacterTextSplitter":
    # langchain_text_splitters' __init__.py eagerly imports every splitter it
    # ships, including SentenceTransformersTokenTextSplitter — which pulls in
    # the full torch/transformers stack even though only the plain character
    # splitter below is used. Deferred here so `import app.main` (and hence
    # server startup) stays fast; this is only paid on an actual ingest call.
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=SEPARATORS,
        keep_separator=True,
    )


def chunk_documents(
    docs: list[Document],
    doc_id: str,
    source_url: str | None = None,
    retrieved_date: str | None = None,
) -> list[Chunk]:
    splitter = build_splitter()
    pieces = splitter.split_documents(docs)

    chunks: list[Chunk] = []
    for i, piece in enumerate(pieces):
        metadata: dict[str, str | int] = {
            "doc_id": doc_id,
            "chunk_index": i,
            "source_file": str(piece.metadata.get("source_file", "unknown")),
        }
        if source_url is not None:
            metadata["source_url"] = source_url
        if retrieved_date is not None:
            metadata["retrieved_date"] = retrieved_date
        if "page" in piece.metadata:
            metadata["page"] = int(piece.metadata["page"])
        chunks.append(
            Chunk(chunk_id=f"{doc_id}:{i}", text=piece.page_content, metadata=metadata)
        )
    return chunks
