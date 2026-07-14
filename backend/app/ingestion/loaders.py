from pathlib import Path

from langchain_core.documents import Document
from pypdf import PdfReader

from app.config import settings


class UnsupportedFileTypeError(ValueError):
    pass


def load_document(path: Path) -> list[Document]:
    suffix = path.suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise UnsupportedFileTypeError(
            f"Unsupported file type {suffix!r}. Allowed: {sorted(settings.allowed_extensions)}"
        )

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        docs = [
            Document(page_content=page.extract_text() or "", metadata={"page": i})
            for i, page in enumerate(reader.pages)
        ]
    else:
        docs = [Document(page_content=path.read_text(encoding="utf-8"), metadata={})]

    for doc in docs:
        doc.metadata["source_file"] = path.name
    return docs
