import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from chat_history import service as history
from database import get_db
from rag.errors import AWSServiceError
from rag.retriever import build_context
from rag.schemas import ChatHistoryResponse, ChatRequest, MessageOut, SessionOut
from rag.services import get_services

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    svc = get_services()
    session = history.get_or_create_session(db, user.id, body.session_id, body.query)
    history.save_message(db, session.id, "user", body.query)
    user_id, session_id = user.id, session.id

    async def event_stream() -> AsyncIterator[str]:
        yield sse({"type": "session", "session_id": session_id})
        cache_key = svc.cache.make_key(user_id, body.query, body.doc_ids)
        try:
            cached = await svc.cache.get(cache_key)  # 1. Redis cache
            if cached:
                yield sse({"type": "sources", "sources": cached["sources"]})
                yield sse({"type": "token", "content": cached["answer"]})
                history.save_message(db, session_id, "assistant", cached["answer"], cached["sources"])
                yield "data: [DONE]\n\n"
                return

            # 2-5. embed -> Pinecone + BM25 -> RRF top 5
            chunks = await svc.retriever.retrieve(body.query, user_id, body.doc_ids)
            sources = [
                {"filename": c.filename, "page_number": c.page_number, "doc_id": c.doc_id,
                 "snippet": c.text[:200]}
                for c in chunks
            ]
            yield sse({"type": "sources", "sources": sources})

            context = build_context(chunks)  # 6. max 12000 chars
            if not context:
                answer = "I couldn't find any relevant content in your documents. Try uploading a document first."
                yield sse({"type": "token", "content": answer})
            else:
                parts: list[str] = []
                async for token in svc.llm.stream_tokens(body.query, context):  # 7. stream
                    parts.append(token)
                    yield sse({"type": "token", "content": token})
                answer = "".join(parts)
                await svc.cache.set(cache_key, {"answer": answer, "sources": sources})  # 8. cache
            history.save_message(db, session_id, "assistant", answer, sources)  # 9. history
        except AWSServiceError as exc:
            logger.error("AWS error: %s", exc.message)
            yield sse({"type": "error", "message": exc.message})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Chat failure")
            yield sse({"type": "error", "message": f"Unexpected error: {exc}"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions", response_model=list[SessionOut])
async def sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[SessionOut]:
    return [SessionOut(id=s.id, title=s.title, created_at=s.created_at) for s in history.list_sessions(db, user.id)]


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def chat_history(
    session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ChatHistoryResponse:
    result = history.get_history(db, user.id, session_id)
    if result is None:
        raise HTTPException(404, "Session not found")
    session, msgs = result
    return ChatHistoryResponse(
        session_id=session.id,
        title=session.title,
        messages=[
            MessageOut(id=m.id, role=m.role, content=m.content, sources=m.sources, created_at=m.created_at)
            for m in msgs
        ],
    )
