import asyncio
from dataclasses import dataclass

from sqlalchemy import select

from database import SessionLocal
from documents.models import Document, DocumentChunk
from rag.bedrock_embeddings import BedrockEmbeddings
from rag.bm25_search import BM25Index, ChunkRecord
from rag.pinecone_store import PineconeStore

RRF_K = 60
MAX_CONTEXT_CHARS = 12000


@dataclass
class RetrievedChunk:
    id: str
    doc_id: int
    filename: str
    page_number: int
    chunk_index: int
    text: str
    score: float


def rrf_merge(rankings: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion: score(d) = sum 1 / (k + rank)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


def build_context(chunks: list[RetrievedChunk], limit: int = MAX_CONTEXT_CHARS) -> str:
    parts: list[str] = []
    total = 0
    for c in chunks:
        block = f"[Source: {c.filename}, page {c.page_number}]\n{c.text}"
        if total + len(block) > limit:
            break
        parts.append(block)
        total += len(block) + 2
    return "\n\n".join(parts)


class HybridRetriever:
    """Pinecone vector search + BM25 keyword search, merged with Reciprocal Rank Fusion."""

    def __init__(self, embeddings: BedrockEmbeddings, store: PineconeStore) -> None:
        self.embeddings = embeddings
        self.store = store
        self._bm25: dict[int, BM25Index] = {}

    def invalidate(self, user_id: int) -> None:
        self._bm25.pop(user_id, None)

    @staticmethod
    def _load_chunks(user_id: int) -> list[ChunkRecord]:
        with SessionLocal() as db:
            rows = db.execute(
                select(DocumentChunk, Document.filename)
                .join(Document, Document.id == DocumentChunk.doc_id)
                .where(DocumentChunk.user_id == user_id)
            ).all()
        return [
            ChunkRecord(
                id=f"{c.doc_id}_{c.chunk_index}",
                doc_id=c.doc_id,
                filename=fn,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                text=c.text,
            )
            for c, fn in rows
        ]

    async def _get_bm25(self, user_id: int) -> BM25Index:
        idx = self._bm25.get(user_id)
        if idx is None:
            chunks = await asyncio.to_thread(self._load_chunks, user_id)
            idx = await asyncio.to_thread(BM25Index, chunks)
            self._bm25[user_id] = idx
        return idx

    async def retrieve(
        self,
        query: str,
        user_id: int,
        doc_ids: list[int] | None = None,
        top_k: int = 5,
        query_vector: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        pc_filter: dict = {"user_id": {"$eq": user_id}}
        if doc_ids:
            pc_filter["doc_id"] = {"$in": [str(d) for d in doc_ids]}
        vector = query_vector or await self.embeddings.embed_text(query)

        matches, bm25 = await asyncio.gather(
            self.store.query(vector, top_k=10, filter=pc_filter),
            self._get_bm25(user_id),
        )
        bm25_hits = bm25.search(query, top_k=10, doc_ids=set(doc_ids) if doc_ids else None)

        by_id: dict[str, RetrievedChunk] = {}
        vector_rank: list[str] = []
        for m in matches:
            md = m.metadata or {}
            cid = f"{int(md['doc_id'])}_{int(md['chunk_index'])}"
            vector_rank.append(cid)
            by_id[cid] = RetrievedChunk(
                id=cid,
                doc_id=int(md["doc_id"]),
                filename=md.get("filename", ""),
                page_number=int(md.get("page_number", 1)),
                chunk_index=int(md["chunk_index"]),
                text=md.get("text", ""),
                score=0.0,
            )
        bm25_rank: list[str] = []
        for h in bm25_hits:
            bm25_rank.append(h.id)
            by_id.setdefault(
                h.id,
                RetrievedChunk(h.id, h.doc_id, h.filename, h.page_number, h.chunk_index, h.text, 0.0),
            )

        scores = rrf_merge([vector_rank, bm25_rank])
        top = sorted(scores, key=lambda i: scores[i], reverse=True)[:top_k]
        result: list[RetrievedChunk] = []
        for cid in top:
            chunk = by_id[cid]
            chunk.score = scores[cid]
            result.append(chunk)
        return result
