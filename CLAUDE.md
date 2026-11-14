# CLAUDE.md — AI Document Assistant with AWS Bedrock (Cloud RAG App)

## Project Overview
Build a production-grade AI Document Assistant using AWS Bedrock — users upload PDF/Word/PPT documents and ask questions. This is the CLOUD version — uses AWS Bedrock (Claude Haiku) for LLM, Amazon Titan for embeddings, and Pinecone for vector storage. No local model downloads needed — everything is cloud API calls.

## Key Difference from Manual Version
- LLM: AWS Bedrock Claude Haiku (NOT Groq) — cloud managed
- Embeddings: Amazon Titan Embeddings V2 (NOT local sentence-transformers) — cloud API
- Vector DB: Pinecone (NOT local ChromaDB) — cloud managed
- Reranker: BM25 keyword scoring only (NOT local CrossEncoder) — no large model download
- Result: No 130MB/90MB downloads, faster first response, cloud-native architecture

## Tech Stack
- Backend: FastAPI + Python 3.10+
- LLM: AWS Bedrock — Claude Haiku 4.5 (via boto3)
- Embeddings: Amazon Titan Text Embeddings V2 (via boto3)
- Vector DB: Pinecone (free tier — cloud managed)
- Keyword Search: BM25 (rank_bm25 — lightweight, local)
- Cache: Redis (Upstash free tier)
- Database: MySQL (SQLAlchemy ORM)
- Auth: JWT (python-jose)
- Frontend: React 18 + React Router v6 + Tailwind CSS + Axios
- Deploy: Docker + Docker Compose

## Folder Structure
```
ai-doc-bedrock/
├── backend/
│   ├── main.py                  # FastAPI app + CORS + lifespan
│   ├── config.py                # env variables (pydantic BaseSettings)
│   ├── database.py              # SQLAlchemy engine + session + Base
│   ├── auth/
│   │   ├── models.py            # User SQLAlchemy model
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routes.py            # POST /auth/register, POST /auth/login
│   │   ├── jwt_handler.py       # create_token, verify_token
│   │   └── dependencies.py      # get_current_user dependency
│   ├── documents/
│   │   ├── models.py            # Document SQLAlchemy model
│   │   ├── schemas.py           # DocumentResponse, UploadResponse
│   │   ├── routes.py            # POST /docs/upload, GET /docs/list, DELETE /docs/{id}
│   │   ├── parser.py            # PDF (pypdf), Word (python-docx), PPT (python-pptx)
│   │   └── chunker.py           # RecursiveCharacterTextSplitter (500 chars, 80 overlap)
│   ├── rag/
│   │   ├── routes.py            # POST /chat (streaming SSE), GET /chat/history
│   │   ├── bedrock_embeddings.py # Amazon Titan Embeddings V2 via boto3
│   │   ├── bedrock_llm.py       # AWS Bedrock Claude Haiku streaming via boto3
│   │   ├── pinecone_store.py    # Pinecone vector store (upsert, query)
│   │   ├── bm25_search.py       # BM25Okapi keyword search
│   │   ├── retriever.py         # HybridRetriever (Pinecone + BM25 + RRF merge)
│   │   ├── cache.py             # Redis cache-aside pattern (TTL 1 hour)
│   │   └── schemas.py           # ChatRequest, ChatHistoryResponse
│   ├── chat_history/
│   │   ├── models.py            # ChatSession, ChatMessage SQLAlchemy models
│   │   └── service.py           # save/get chat history
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Routes setup
│   │   ├── api/
│   │   │   └── api.js           # Axios instance + interceptors
│   │   ├── hooks/
│   │   │   ├── useAuth.js       # login, logout, token management
│   │   │   └── useStreamChat.js # SSE streaming hook
│   │   ├── pages/
│   │   │   ├── Login.jsx        # Login + Register form
│   │   │   ├── Dashboard.jsx    # Document upload + list
│   │   │   └── Chat.jsx         # Chat interface
│   │   ├── components/
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── FileUpload.jsx
│   │   │   ├── DocumentList.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx  # with react-markdown
│   │   │   ├── StreamingText.jsx
│   │   │   └── Sidebar.jsx
│   │   └── index.css
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Backend Requirements

### Config (config.py)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AWS Bedrock
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "ap-southeast-2"
    bedrock_model_id: str = "anthropic.claude-3-5-haiku-20241022-v1:0"
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"
    
    # Pinecone
    pinecone_api_key: str
    pinecone_index_name: str = "ai-doc-bedrock"
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    class Config:
        env_file = ".env"
```

### AWS Bedrock Embeddings (bedrock_embeddings.py)
```python
import boto3
import json

class BedrockEmbeddings:
    def __init__(self, settings):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self.model_id = settings.bedrock_embedding_model
    
    def embed_text(self, text: str) -> list[float]:
        body = json.dumps({
            "inputText": text,
            "dimensions": 512,
            "normalize": True
        })
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())
        return result["embedding"]
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]
```

### AWS Bedrock LLM Streaming (bedrock_llm.py)
```python
import boto3
import json

class BedrockLLM:
    def __init__(self, settings):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        self.model_id = settings.bedrock_model_id
    
    async def stream_response(self, query: str, context: str):
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "temperature": 0.1,
            "system": f"You are a helpful document assistant. Answer ONLY from the provided context. If the answer is not in the context, say so. Be concise.\n\nContext:\n{context}",
            "messages": [
                {"role": "user", "content": query}
            ]
        })
        
        response = self.client.invoke_model_with_response_stream(
            modelId=self.model_id,
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        
        stream = response.get("body")
        for event in stream:
            chunk = event.get("chunk")
            if chunk:
                data = json.loads(chunk.get("bytes").decode())
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"
        
        yield "data: [DONE]\n\n"
```

### Pinecone Vector Store (pinecone_store.py)
```python
from pinecone import Pinecone, ServerlessSpec

class PineconeStore:
    def __init__(self, settings):
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        
        # Create index if not exists
        if self.index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=self.index_name,
                dimension=512,  # Titan Embeddings V2 dimension
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        self.index = self.pc.Index(self.index_name)
    
    def upsert(self, vectors: list[dict]):
        # vectors = [{"id": "chunk_1", "values": [...], "metadata": {...}}]
        self.index.upsert(vectors=vectors, namespace="default")
    
    def query(self, vector: list[float], top_k: int = 10, filter: dict = None):
        results = self.index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace="default",
            filter=filter
        )
        return results.matches
    
    def delete_by_doc(self, doc_id: str):
        self.index.delete(filter={"doc_id": doc_id}, namespace="default")
```

### Hybrid Retriever (retriever.py)
- Pinecone vector search (top 10)
- BM25 keyword search (top 10)
- Reciprocal Rank Fusion merge (k=60)
- Return top 5 merged results
- NO CrossEncoder reranker — RRF scoring is sufficient for this cloud version

### Authentication (same pattern as Project 1)
- POST /auth/register — email, password, name. bcrypt hash. Return JWT.
- POST /auth/login — verify. Return JWT.
- JWT: HS256, 24hr expiry.
- Dependency: get_current_user.

### Document Management
- POST /docs/upload — PDF, DOCX, PPTX. Max 10MB.
- Parse → Chunk (500 chars, 80 overlap) → Embed with Titan → Store in Pinecone
- Each chunk metadata: {doc_id, filename, page_number, chunk_index, user_id}
- GET /docs/list — user's documents
- DELETE /docs/{id} — delete from MySQL + Pinecone

### RAG Chat
- POST /chat — StreamingResponse (text/event-stream)
- Flow:
  1. Check Redis cache
  2. Embed query with Titan Embeddings
  3. Pinecone vector search (top 10)
  4. BM25 keyword search (top 10)
  5. RRF merge → top 5
  6. Build context (max 12000 chars)
  7. Stream from Bedrock Claude Haiku
  8. Cache result in Redis (TTL: 3600s)
  9. Save to chat history

### Chat History
- GET /chat/history/{session_id}
- Save with session management

### CORS
- Allow localhost:3000 and localhost:5173

## Frontend Requirements
- IDENTICAL to Project 1 frontend — same UI, same hooks, same components
- React + Tailwind + React Router v6
- Login, Dashboard (upload), Chat (streaming)
- react-markdown for message rendering
- Dark mode support
- useStreamChat hook for SSE parsing

## Docker
### docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    environment:
      - DB_HOST=host.docker.internal
  frontend:
    build: ./frontend
    ports: ["3000:80"]
    depends_on: [backend]
```

## Build Order
1. backend/config.py + database.py + main.py
2. auth/ (register, login, JWT — same as Project 1)
3. documents/ (upload, parse, chunk)
4. rag/bedrock_embeddings.py (Titan API)
5. rag/pinecone_store.py (Pinecone setup)
6. rag/bm25_search.py (keyword search)
7. rag/retriever.py (hybrid: Pinecone + BM25 + RRF)
8. rag/bedrock_llm.py (Claude Haiku streaming)
9. rag/cache.py (Redis)
10. rag/routes.py (chat endpoint)
11. chat_history/
12. Frontend (same as Project 1 — copy pattern)
13. Docker setup
14. Tests + README
15. Git init + .gitignore + commit

## Key Python Packages
```
fastapi
uvicorn
boto3              # AWS SDK — Bedrock calls
pinecone-client    # Pinecone vector store
python-jose[cryptography]
passlib[bcrypt]
sqlalchemy
pymysql
redis
pypdf
python-docx
python-pptx
python-multipart
pydantic-settings
rank-bm25
python-dotenv
httpx
```

## README must highlight
- "Cloud-native RAG pipeline using AWS Bedrock"
- "Amazon Titan Embeddings V2 for semantic search"
- "Pinecone serverless vector database"
- "Zero local model downloads — all cloud API calls"
- Comparison table: Manual (Project 1) vs Cloud (this project)
- Architecture diagram showing AWS services used

## Important Rules
- Use async/await everywhere
- Pydantic v2 for all schemas
- boto3 client — NOT langchain Bedrock wrapper (show raw AWS SDK usage)
- Error handling for AWS API errors (throttling, access denied)
- .env for all secrets
- Type hints on all functions
- README must show Manual vs Cloud comparison