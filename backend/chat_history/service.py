import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from chat_history.models import ChatMessage, ChatSession


def get_or_create_session(db: Session, user_id: int, session_id: str | None, first_query: str) -> ChatSession:
    if session_id:
        session = db.get(ChatSession, session_id)
        if session and session.user_id == user_id:
            return session
    session = ChatSession(id=str(uuid.uuid4()), user_id=user_id, title=first_query[:60])
    db.add(session)
    db.commit()
    return session


def save_message(
    db: Session, session_id: str, role: str, content: str, sources: list[dict] | None = None
) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content, sources=sources)
    db.add(msg)
    db.commit()
    return msg


def get_history(db: Session, user_id: int, session_id: str) -> tuple[ChatSession, list[ChatMessage]] | None:
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user_id:
        return None
    msgs = db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)
    ).all()
    return session, list(msgs)


def list_sessions(db: Session, user_id: int) -> list[ChatSession]:
    return list(
        db.scalars(
            select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
        ).all()
    )
