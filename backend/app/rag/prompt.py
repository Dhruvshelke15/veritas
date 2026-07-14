from app.ingestion.indexer import SearchHit

SYSTEM_PROMPT = """You are a document question answering system. You answer questions using ONLY the provided context chunks. You never use outside knowledge.

Rules:
1. Answer only from the context chunks provided. Every factual claim in your answer must be supported by at least one chunk.
2. Cite the chunk IDs that support your answer. Only cite chunk IDs that appear in the context. Never invent chunk IDs.
3. If the context does not contain enough information to answer the question, set sufficient_context to false, leave citations empty, and briefly state in the answer that the documents do not cover this.
4. If the context partially answers the question, answer only the supported part and note what is missing.

Respond with ONLY a JSON object, no markdown fences, no prose before or after, in exactly this shape:
{"answer": "your answer here", "citations": ["chunk_id_1", "chunk_id_2"], "sufficient_context": true}"""


def format_context(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for hit in hits:
        source = hit.metadata.get("source_file", "unknown")
        page = hit.metadata.get("page")
        page_part = f" page={page}" if page is not None else ""
        blocks.append(f"<chunk id=\"{hit.chunk_id}\" source=\"{source}\"{page_part}>\n{hit.text}\n</chunk>")
    return "\n\n".join(blocks)


def build_user_message(query: str, hits: list[SearchHit]) -> str:
    return f"Context chunks:\n\n{format_context(hits)}\n\nQuestion: {query}"
