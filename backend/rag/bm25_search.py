import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

_TOKEN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass
class ChunkRecord:
    id: str
    doc_id: int
    filename: str
    page_number: int
    chunk_index: int
    text: str


class BM25Index:
    """BM25Okapi keyword index over a user's chunks."""

    def __init__(self, chunks: list[ChunkRecord]) -> None:
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks]) if chunks else None

    def search(self, query: str, top_k: int = 10, doc_ids: set[int] | None = None) -> list[ChunkRecord]:
        if self.bm25 is None:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        results: list[ChunkRecord] = []
        for i in ranked:
            if scores[i] <= 0:
                break
            if doc_ids is not None and self.chunks[i].doc_id not in doc_ids:
                continue
            results.append(self.chunks[i])
            if len(results) >= top_k:
                break
        return results
