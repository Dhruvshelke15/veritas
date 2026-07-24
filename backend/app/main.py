import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.classifier.predictor import get_classifier
from app.config import settings
from app.eval import storage as eval_storage
from app.ingestion.chunking import chunk_documents, compute_doc_id
from app.ingestion.indexer import DocumentSummary, SearchHit, index_chunks, list_documents, similarity_search
from app.ingestion.loaders import UnsupportedFileTypeError, load_document
from app.rag.generator import get_generator
from app.rag.pipeline import AskResult, ask_routed
from app.rag.streaming import AnswerDeltaEvent, FinalEvent, MetaEvent, ask_routed_stream

app = FastAPI(title="Veritas", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    query_category: str | None
    category_confidence: float | None
    routing_action: str

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
            query_category=result.query_category,
            category_confidence=result.category_confidence,
            routing_action=result.routing_action,
        )


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest) -> AskResponse:
    classifier = get_classifier()
    classification = classifier.classify(request.query) if classifier is not None else None
    result = ask_routed(
        request.query,
        generator=get_generator(),
        classification=classification,
        top_k=request.top_k,
    )
    return AskResponse.from_result(result)


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_events(query: str, top_k: int) -> Iterator[str]:
    classifier = get_classifier()
    classification = classifier.classify(query) if classifier is not None else None
    for event in ask_routed_stream(
        query, generator=get_generator(), classification=classification, top_k=top_k
    ):
        if isinstance(event, MetaEvent):
            yield _sse_event(
                {
                    "type": "meta",
                    "query_category": event.query_category,
                    "category_confidence": event.category_confidence,
                    "routing_action": event.routing_action,
                }
            )
        elif isinstance(event, AnswerDeltaEvent):
            yield _sse_event({"type": "answer_delta", "text": event.text})
        elif isinstance(event, FinalEvent):
            yield _sse_event({"type": "final", **AskResponse.from_result(event.result).model_dump()})


@app.post("/ask/stream")
def ask_stream_endpoint(request: AskRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_events(request.query, request.top_k), media_type="text/event-stream"
    )


class DocumentResponse(BaseModel):
    doc_id: str
    source_file: str
    source_url: str | None
    retrieved_date: str | None
    chunk_count: int

    @classmethod
    def from_summary(cls, summary: DocumentSummary) -> "DocumentResponse":
        return cls(
            doc_id=summary.doc_id,
            source_file=summary.source_file,
            source_url=summary.source_url,
            retrieved_date=summary.retrieved_date,
            chunk_count=summary.chunk_count,
        )


@app.get("/documents", response_model=list[DocumentResponse])
def documents_endpoint() -> list[DocumentResponse]:
    return [DocumentResponse.from_summary(d) for d in list_documents()]


class EvalRunSummaryResponse(BaseModel):
    run_id: int
    started_at: str
    retrieval_hit_rate: float | None
    mean_faithfulness: float | None
    classifier_accuracy: dict[str, float] | None


class EvalQuestionResultResponse(BaseModel):
    question_id: str
    query: str
    category: str
    retrieval_hit: bool | None
    faithfulness_score: int | None
    faithfulness_rationale: str | None
    classifier_predicted: str | None
    classifier_correct: bool | None
    sufficient_context: bool
    routing_action: str
    answer: str


class EvalRunDetailResponse(BaseModel):
    run: EvalRunSummaryResponse
    questions: list[EvalQuestionResultResponse]


@app.get("/eval/runs", response_model=list[EvalRunSummaryResponse])
def eval_runs_endpoint() -> list[EvalRunSummaryResponse]:
    conn = eval_storage.connect(settings.eval_db_path)
    return [EvalRunSummaryResponse(**row) for row in eval_storage.list_runs(conn)]


@app.get("/eval/runs/{run_id}", response_model=EvalRunDetailResponse)
def eval_run_detail_endpoint(run_id: int) -> EvalRunDetailResponse:
    conn = eval_storage.connect(settings.eval_db_path)
    detail = eval_storage.get_run_detail(conn, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No eval run with id {run_id}")
    return EvalRunDetailResponse(
        run=EvalRunSummaryResponse(**detail["run"]),
        questions=[EvalQuestionResultResponse(**q) for q in detail["questions"]],
    )
