from documents.chunker import chunk_text
from rag.bm25_search import BM25Index, ChunkRecord
from rag.cache import ResponseCache
from rag.retriever import RetrievedChunk, build_context, rrf_merge


def test_chunker_sizes_and_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(400))
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)
    assert chunks[0][-20:].strip().split()[-1] in chunks[1]


def test_chunker_empty() -> None:
    assert chunk_text("   ") == []


def test_rrf_prefers_items_in_both_lists() -> None:
    scores = rrf_merge([["a", "b", "c"], ["b", "d"]])
    assert max(scores, key=scores.get) == "b"
    assert abs(scores["a"] - 1 / 61) < 1e-9


def test_bm25_ranks_relevant_chunk_first() -> None:
    chunks = [
        ChunkRecord("1_0", 1, "a.pdf", 1, 0, "the cat sat on the mat"),
        ChunkRecord("1_1", 1, "a.pdf", 1, 1, "quarterly revenue grew by ten percent"),
        ChunkRecord("2_0", 2, "b.pdf", 1, 0, "dogs bark loudly at night"),
    ]
    hits = BM25Index(chunks).search("revenue growth", top_k=3)
    assert hits and hits[0].id == "1_1"
    assert BM25Index(chunks).search("revenue", doc_ids={2}) == []


def test_context_limit() -> None:
    chunks = [RetrievedChunk(str(i), 1, "f.pdf", 1, i, "x" * 5000, 0.1) for i in range(5)]
    assert len(build_context(chunks, limit=12000)) <= 12000


def test_cache_key_stable() -> None:
    k1 = ResponseCache.make_key(1, "Hello ", [2, 1])
    k2 = ResponseCache.make_key(1, "hello", [1, 2])
    assert k1 == k2 != ResponseCache.make_key(2, "hello", [1, 2])
