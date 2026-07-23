import threading
from dataclasses import dataclass, replace

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.config import settings
from app.ingestion.chunking import Chunk


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    text: str
    distance: float
    metadata: dict[str, str | int]


@dataclass(frozen=True)
class DocumentSummary:
    doc_id: str
    source_file: str
    source_url: str | None
    retrieved_date: str | None
    chunk_count: int


_collection: Collection | None = None
_collection_lock = threading.Lock()


def get_collection() -> Collection:
    # Double-checked locking: chromadb's PersistentClient registry isn't safe
    # against concurrent first-time creation for the same path (FastAPI runs
    # sync endpoints in a thread pool, and React StrictMode's double
    # effect-invocation in dev is enough to trigger two simultaneous
    # cold-start calls here). A plain @lru_cache doesn't help -- it only
    # dedupes completed results, not concurrent in-flight calls.
    global _collection
    if _collection is None:
        with _collection_lock:
            if _collection is None:
                client = chromadb.PersistentClient(path=str(settings.chroma_dir))
                embedding_fn = SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)
                _collection = client.get_or_create_collection(
                    name=settings.collection_name,
                    embedding_function=embedding_fn,
                    metadata={"hnsw:space": "cosine"},
                )
    return _collection


def index_chunks(chunks: list[Chunk]) -> int:
    if not chunks:
        return 0
    collection = get_collection()
    collection.upsert(
        ids=[c.chunk_id for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )
    return len(chunks)


def similarity_search(query: str, top_k: int | None = None) -> list[SearchHit]:
    k = top_k or settings.default_top_k
    collection = get_collection()
    result = collection.query(query_texts=[query], n_results=k)

    ids = result["ids"][0]
    documents = (result.get("documents") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]

    return [
        SearchHit(
            chunk_id=ids[i],
            text=documents[i],
            distance=float(distances[i]),
            metadata=dict(metadatas[i]) if metadatas[i] else {},
        )
        for i in range(len(ids))
    ]


def list_documents() -> list[DocumentSummary]:
    collection = get_collection()
    result = collection.get(include=["metadatas"])
    metadatas = result.get("metadatas") or []

    by_doc_id: dict[str, DocumentSummary] = {}
    for metadata in metadatas:
        doc_id = str(metadata.get("doc_id", "unknown"))
        existing = by_doc_id.get(doc_id)
        if existing is None:
            source_url = metadata.get("source_url")
            retrieved_date = metadata.get("retrieved_date")
            by_doc_id[doc_id] = DocumentSummary(
                doc_id=doc_id,
                source_file=str(metadata.get("source_file", "unknown")),
                source_url=str(source_url) if source_url is not None else None,
                retrieved_date=str(retrieved_date) if retrieved_date is not None else None,
                chunk_count=1,
            )
        else:
            by_doc_id[doc_id] = replace(existing, chunk_count=existing.chunk_count + 1)

    return sorted(by_doc_id.values(), key=lambda d: d.source_file)
