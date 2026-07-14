from datetime import date
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import SearchHit, index_chunks, similarity_search
from app.ingestion.loaders import UnsupportedFileTypeError, load_document
from app.rag.generator import get_generator
from app.rag.pipeline import AskResult, ask

app = FastAPI(title="Veritas", version="0.1.0")


class IngestResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_indexed: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=settings.default_top_k, ge=1, le=20)


class SearchHitResponse(BaseModel):
    chunk_id: str
    text: str
    distance: float
    metadata: dict[str, str | int]

    @classmethod
    def from_hit(cls, hit: SearchHit) -> "SearchHitResponse":
        return cls(
            chunk_id=hit.chunk_id, text=hit.text, distance=hit.distance, metadata=hit.metadata
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile, source_url: str | None = Form(default=None)) -> IngestResponse:
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type {suffix!r}. Allowed: {sorted(settings.allowed_extensions)}",
        )

    file_bytes = await file.read()
    doc_id = compute_doc_id(file_bytes)

    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = settings.upload_dir / f"{doc_id}{suffix}"
    saved_path.write_bytes(file_bytes)

    try:
        docs = load_document(saved_path)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    chunks = chunk_documents(
        docs, doc_id, source_url=source_url, retrieved_date=date.today().isoformat()
    )
    count = index_chunks(chunks)
    return IngestResponse(doc_id=doc_id, filename=file.filename, chunks_indexed=count)


@app.post("/search", response_model=list[SearchHitResponse])
def search(request: SearchRequest) -> list[SearchHitResponse]:
    hits = similarity_search(request.query, top_k=request.top_k)
    return [SearchHitResponse.from_hit(h) for h in hits]


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=settings.default_top_k, ge=1, le=20)


class CitationResponse(BaseModel):
    chunk_id: str
    text: str
    source_file: str
    page: int | None
    source_url: str | None
    retrieved_date: str | None


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    sufficient_context: bool
    hallucinated_citations: list[str]
    parse_failed: bool

    @classmethod
    def from_result(cls, result: AskResult) -> "AskResponse":
        return cls(
            answer=result.answer,
            citations=[
                CitationResponse(
                    chunk_id=c.chunk_id,
                    text=c.text,
                    source_file=c.source_file,
                    page=c.page,
                    source_url=c.source_url,
                    retrieved_date=c.retrieved_date,
                )
                for c in result.citations
            ],
            sufficient_context=result.sufficient_context,
            hallucinated_citations=result.hallucinated_citations,
            parse_failed=result.parse_failed,
        )


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    result = ask(request.query, generator=get_generator(), top_k=request.top_k)
    return AskResponse.from_result(result)
