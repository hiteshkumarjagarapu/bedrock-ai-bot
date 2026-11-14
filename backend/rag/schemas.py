from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    doc_ids: list[int] | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    title: str
    messages: list[MessageOut]


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
