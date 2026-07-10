"""Test fixtures.

Each test gets a fresh in-memory-ish SQLite database (a temp file, since WAL
needs a file). Alembic runs `upgrade head` so the schema matches production.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event

from app import db as db_module
from app.config import settings


@pytest.fixture()
def tmp_db_url(monkeypatch, tmp_path) -> str:
    """Point the app at a throwaway SQLite file for this test."""
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file.as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    # Reset the module-level engine + session factory to use the new URL.
    db_module.engine.dispose()
    new_engine = create_engine(
        url,
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(new_engine, "connect")
    def _pragma(dbapi_conn, _record):  # type: ignore[no-untyped-def]
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        # Mirrors app.db._set_sqlite_pragma so tests run with the same
        # lock-wait behavior as production connections.
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

    monkeypatch.setattr(db_module, "engine", new_engine)
    from sqlalchemy.orm import sessionmaker

    new_session = sessionmaker(bind=new_engine, autoflush=False, autocommit=False, future=True)
    monkeypatch.setattr(db_module, "SessionLocal", new_session)
    yield url
    new_engine.dispose()


@pytest.fixture()
def client(tmp_db_url) -> Iterator[TestClient]:
    """TestClient with the schema migrated up."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", tmp_db_url)
    command.upgrade(cfg, "head")

    from app.main import app

    with TestClient(app) as c:
        yield c
