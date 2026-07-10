"""SQLAlchemy engine, session factory, and the `get_db` dependency.

SQLite is opened in WAL mode with foreign keys enforced on every connection
so that concurrent reads and FK constraints behave predictably.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


engine: Engine = create_engine(
    settings.database_url,
    # SQLite needs check_same_thread=False so FastAPI's threadpool can share
    # the engine. WAL + a single writer keeps the model consistent.
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        """Enable WAL, foreign keys, relaxed synchronous flush, and a busy timeout."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        # Writers wait up to 30s for the lock instead of failing fast with
        # "database is locked" — ingest holds a write transaction across disk
        # file IO, so concurrent workers/requests need headroom.
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yield a session, always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
