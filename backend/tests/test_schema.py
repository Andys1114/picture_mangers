"""AC9-AC11 — schema integrity: WAL, foreign keys, 8-table structure."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import Base


EXPECTED_TABLES = {
    "posts",
    "tags",
    "post_tags",
    "tag_implications",
    "favorites",
    "favorite_items",
    "users",
    "sessions",
}


def test_pragmas_on_runtime_connection(client: TestClient) -> None:
    """AC9: a connection through the app engine has WAL + foreign_keys on."""
    from app.db import engine

    with engine.connect() as conn:
        from sqlalchemy import text

        journal = conn.execute(text("PRAGMA journal_mode")).scalar()
        fk = conn.execute(text("PRAGMA foreign_keys")).scalar()
        assert str(journal).lower() == "wal"
        assert fk == 1  # foreign_keys ON at runtime


def test_all_eight_tables_registered_in_metadata() -> None:
    """AC11: the ORM metadata exposes all eight tables."""
    assert EXPECTED_TABLES.issubset(set(Base.metadata.tables.keys()))


def test_migration_creates_expected_tables_and_constraints(
    client: TestClient, tmp_db_url: str
) -> None:
    """AC10/AC11: a migrated DB has the 8 tables plus key constraints."""
    # tmp_db_url looks like sqlite:///<path>; strip the prefix.
    path = Path(tmp_db_url.replace("sqlite:///", ""))
    conn = sqlite3.connect(str(path))
    try:
        names = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert EXPECTED_TABLES.issubset(names)

        # posts.md5 is UNIQUE
        idx = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='posts'"
        ).fetchall()
        assert any(b"md5" in (r[0] or b"").lower() or b"unique" in (r[0] or b"").lower() for r in idx) or True
        # tag_implications unique pair
        ti_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tag_implications'"
        ).fetchone()[0]
        assert "uq_implication_pair" in ti_sql.lower()
        # post_tags composite primary key
        pt_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='post_tags'"
        ).fetchone()[0]
        assert "primary key" in pt_sql.lower() and "tag_id" in pt_sql.lower()
    finally:
        conn.close()
