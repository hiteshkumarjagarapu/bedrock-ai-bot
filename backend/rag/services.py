from functools import lru_cache

from config import get_settings
from rag.bedrock_embeddings import BedrockEmbeddings
from rag.bedrock_llm import BedrockLLM
from rag.cache import ResponseCache
from rag.pinecone_store import PineconeStore
from rag.retriever import HybridRetriever


class Services:
    def __init__(self) -> None:
        s = get_settings()
        self.embeddings = BedrockEmbeddings(s)
        self.store = PineconeStore(s)
        self.llm = BedrockLLM(s)
        self.cache = ResponseCache(s)
        self.retriever = HybridRetriever(self.embeddings, self.store)


@lru_cache
def get_services() -> Services:
    return Services()
