import asyncio
import time
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from config import Settings

NAMESPACE = "default"
DIMENSION = 512


class PineconeStore:
    def __init__(self, settings: Settings) -> None:
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=DIMENSION,  # Titan Embeddings V2 (512-dim)
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            while not self.pc.describe_index(self.index_name).status["ready"]:
                time.sleep(1)
        self.index = self.pc.Index(self.index_name)

    def _upsert_sync(self, vectors: list[dict[str, Any]]) -> None:
        for i in range(0, len(vectors), 100):
            self.index.upsert(vectors=vectors[i : i + 100], namespace=NAMESPACE)

    async def upsert(self, vectors: list[dict[str, Any]]) -> None:
        await asyncio.to_thread(self._upsert_sync, vectors)

    def _query_sync(self, vector: list[float], top_k: int, filter: dict | None) -> list[Any]:
        res = self.index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace=NAMESPACE,
            filter=filter,
        )
        return list(res.matches)

    async def query(self, vector: list[float], top_k: int = 10, filter: dict | None = None) -> list[Any]:
        return await asyncio.to_thread(self._query_sync, vector, top_k, filter)

    def _delete_sync(self, doc_id: str) -> None:
        self.index.delete(filter={"doc_id": {"$eq": doc_id}}, namespace=NAMESPACE)

    async def delete_by_doc(self, doc_id: str) -> None:
        await asyncio.to_thread(self._delete_sync, doc_id)
