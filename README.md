# AI Document Assistant — AWS Bedrock (Cloud RAG)

- **Cloud-native RAG pipeline using AWS Bedrock**
- **Amazon Titan Embeddings V2 for semantic search**
- **Pinecone serverless vector database**
- **Zero local model downloads — all cloud API calls**

Upload PDF / Word / PowerPoint documents, then ask questions and get streamed, source-cited answers.

## Architecture

```
 React (Vite, Tailwind)  ──SSE──▶  FastAPI
                                     │
        ┌────────────────────────────┼─────────────────────────────┐
        ▼                            ▼                             ▼
  MySQL (users, docs,        Redis / Upstash              ┌──── AWS ────────────────┐
  chunks, chat history)      (answer cache, 1h)           │ Bedrock: Titan Embed V2 │
                                                          │ Bedrock: Claude Haiku   │
                                                          └─────────────────────────┘
                                     ▼
                         Pinecone serverless (512-d cosine)

 Query ─▶ Redis cache ─▶ Titan embed ─▶ Pinecone top 10 ┐
                                        BM25 top 10 ────┴▶ RRF (k=60) ─▶ top 5 ─▶ Claude Haiku (stream)
```

## Manual (Project 1) vs Cloud (this project)

| Aspect | Manual (Project 1) | Cloud (this project) |
|---|---|---|
| LLM | Groq | AWS Bedrock — Claude Haiku 4.5 |
| Embeddings | Local sentence-transformers | Amazon Titan Text Embeddings V2 |
| Vector DB | Local ChromaDB | Pinecone serverless |
| Reranker | Local CrossEncoder | BM25 + Reciprocal Rank Fusion |
| Model downloads | ~130MB + ~90MB | None |
| First response | Slow (model load) | Fast |
| Scaling | Single machine | Managed cloud services |

## Setup

1. Create `backend/.env` from `backend/.env.example` (AWS keys, Pinecone key, Upstash Redis URL, MySQL URL, JWT secret).
   Enable model access for Titan Embeddings V2 and Claude Haiku in the Bedrock console.
   Outside the US, Claude needs a regional inference profile ID (e.g. `au.anthropic.claude-haiku-4-5-20251001-v1:0`).
2. Backend:
   ```
   cd backend
   python -m venv .venv && .venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn main:app --port 8000
   ```
   The MySQL database and the Pinecone index are created automatically on startup.
3. Frontend:
   ```
   cd frontend
   npm install
   npm run dev        # http://localhost:5173  (set VITE_API_URL if the API is not on :8000)
   ```
4. Docker: `docker compose up --build` (use `host.docker.internal` as the MySQL host in `DATABASE_URL`). UI on :3000, API on :8000.

## Tests

```
cd backend
pytest tests/test_unit.py                 # chunker, BM25, RRF, cache key
python tests/smoke_e2e.py http://localhost:8000   # full flow against a running server and real AWS/Pinecone
```

## API

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register`, `/auth/login` | Returns JWT (HS256, 24h) |
| POST | `/docs/upload` | PDF/DOCX/PPTX, max 10MB |
| GET | `/docs/list` | Your documents |
| DELETE | `/docs/{id}` | Removes from MySQL and Pinecone |
| POST | `/chat` | Streaming SSE answer |
| GET | `/chat/sessions`, `/chat/history/{session_id}` | Chat history |

Boto3 is used directly (no LangChain wrapper); AWS throttling and access-denied errors are translated into clear messages.
