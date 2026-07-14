from dataclasses import dataclass
from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_collection() -> Collection:
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=settings.embedding_model)
    return client.get_or_create_collection(
        name=settings.collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


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
