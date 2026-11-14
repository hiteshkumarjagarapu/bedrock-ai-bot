from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def ensure_database() -> None:
    """Create the MySQL database if it doesn't exist yet."""
    url = make_url(settings.database_url)
    server_engine = create_engine(url.set(database=None))
    with server_engine.connect() as conn:
        conn.exec_driver_sql(
            f"CREATE DATABASE IF NOT EXISTS `{url.database}` CHARACTER SET utf8mb4"
        )
    server_engine.dispose()


def init_db() -> None:
    import auth.models  # noqa: F401
    import chat_history.models  # noqa: F401
    import documents.models  # noqa: F401

    ensure_database()
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
