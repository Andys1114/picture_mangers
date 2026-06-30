"""AC9-AC11 — schema integrity: WAL, foreign keys, 8-table structure."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

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
        # sqlite3 returns sql as str; guard against NULL rows.
        idx_sqls = [(r[0] or "").lower() for r in idx]
        assert any("md5" in s or "unique" in s for s in idx_sqls)
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


def test_post_schema_matches_grilling_decisions(client: TestClient, tmp_db_url: str) -> None:
    """AC1: fav_count dropped; duplicate_of_id added with self-FK SET NULL;
    partial unique index on (source_site, source_id) has a WHERE predicate."""
    path = Path(tmp_db_url.replace("sqlite:///", ""))
    conn = sqlite3.connect(str(path))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(posts)")}
        assert "fav_count" not in cols, "fav_count must be dropped"
        assert "duplicate_of_id" in cols, "duplicate_of_id must exist"

        # Self-referencing FK with ondelete=SET NULL.
        fks = conn.execute("PRAGMA foreign_key_list(posts)").fetchall()
        # pragma row: (id, seq, table, from, to, on_update, on_delete, match)
        dup_fk = [f for f in fks if f[3] == "duplicate_of_id"]
        assert dup_fk, "duplicate_of_id must have a foreign key"
        assert dup_fk[0][2] == "posts", "duplicate_of_id must self-reference posts"
        assert dup_fk[0][6].upper() == "SET NULL", "ondelete must be SET NULL"

        # Partial unique index with a WHERE predicate.
        idx_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='ix_posts_source_site_source_id'"
        ).fetchone()[0]
        sql_lower = idx_sql.lower()
        assert "unique" in sql_lower, "source index must be unique"
        assert "where" in sql_lower, "source index must be a partial index (WHERE predicate)"
        assert "source_site is not null" in sql_lower
        assert "source_id is not null" in sql_lower
    finally:
        conn.close()


def test_migration_downgrade_reverses_schema_changes(tmp_db_url: str) -> None:
    """AC2: downgrade -1 reverses the pending-schema-align migration —
    fav_count returns, duplicate_of_id and the partial index disappear."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", tmp_db_url)
    # tmp_db_url only stands up the engine; upgrade to head first so there is
    # exactly one revision to step back from.
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "-1")

    path = Path(tmp_db_url.replace("sqlite:///", ""))
    conn = sqlite3.connect(str(path))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(posts)")}
        assert "fav_count" in cols, "downgrade must restore fav_count"
        assert "duplicate_of_id" not in cols, "downgrade must drop duplicate_of_id"

        idx_names = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='posts'"
            )
        }
        assert "ix_posts_source_site_source_id" not in idx_names, "downgrade must drop the partial index"
    finally:
        conn.close()
