"""AC9-AC11 — schema integrity: WAL, foreign keys, 8-table structure."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
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
    """AC2: downgrading past the schema-align migration reverses it —
    fav_count returns, duplicate_of_id and the partial index disappear.

    Head now also includes the session.safe_mode revision on top of the
    schema-align revision, so we step back to the initial revision to reverse
    the align migration.
    """
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", tmp_db_url)
    # tmp_db_url only stands up the engine; upgrade to head first.
    command.upgrade(cfg, "head")
    # Step back past the schema-align migration (74035bafb648) to the initial
    # schema (f3d99311f0cf), which still carries fav_count.
    command.downgrade(cfg, "f3d99311f0cf")

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


_NEW_INDEXES = {
    "ux_favorites_name",
    "ix_posts_rating",
    "ix_posts_duplicate_of_id",
    "ix_favorite_items_post_id",
}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    return {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        if r[0] is not None
    }


def test_new_indexes_and_favorites_name_unique(client: TestClient, tmp_db_url: str) -> None:
    # audit #11 + #38: head schema carries the read-path indexes and enforces
    # unique favorite names via a unique index.
    path = Path(tmp_db_url.replace("sqlite:///", ""))
    conn = sqlite3.connect(str(path))
    try:
        assert _NEW_INDEXES <= _index_names(conn)
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='ux_favorites_name'"
        ).fetchone()[0]
        assert "unique" in sql.lower(), "favorites.name index must be UNIQUE"
    finally:
        conn.close()


def test_favorites_dedup_migration_preserves_items(tmp_db_url: str) -> None:
    # audit #11: the unique-name migration renames duplicate rows to
    # "<name>-<id>" and must NOT lose favorite_items rows (a batch-mode table
    # rebuild would fire ON DELETE CASCADE under PRAGMA foreign_keys=ON).
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", tmp_db_url)
    # Stand on the previous head, where duplicate names are still possible.
    command.upgrade(cfg, "ffcb2b9d04bb")

    path = Path(tmp_db_url.replace("sqlite:///", ""))
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "INSERT INTO posts (file_path, thumb_path, preview_path, file_ext,"
            " is_animated, width, height, file_size, md5, is_duplicate, rating)"
            " VALUES ('p', 't', 'v', 'png', 0, 1, 1, 1, 'm1', 0, 'safe')"
        )
        post_id = conn.execute("SELECT id FROM posts").fetchone()[0]
        conn.execute("INSERT INTO favorites (name) VALUES ('默认收藏')")
        conn.execute("INSERT INTO favorites (name) VALUES ('默认收藏')")
        keeper_id, dupe_id = [
            r[0] for r in conn.execute("SELECT id FROM favorites ORDER BY id")
        ]
        conn.execute(
            "INSERT INTO favorite_items (favorite_id, post_id, position) VALUES (?, ?, 0)",
            (keeper_id, post_id),
        )
        conn.execute(
            "INSERT INTO favorite_items (favorite_id, post_id, position) VALUES (?, ?, 0)",
            (dupe_id, post_id),
        )
        conn.commit()
    finally:
        conn.close()

    command.upgrade(cfg, "head")

    conn = sqlite3.connect(str(path))
    try:
        names = sorted(r[0] for r in conn.execute("SELECT name FROM favorites"))
        assert names == ["默认收藏", f"默认收藏-{dupe_id}"], "later duplicate renamed to name-id"
        # Membership rows survive the migration.
        assert conn.execute("SELECT COUNT(*) FROM favorite_items").fetchone()[0] == 2
        # Uniqueness is now enforced at the DB level.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO favorites (name) VALUES ('默认收藏')")
    finally:
        conn.close()

    # Downgrade drops all four indexes (renames are a one-way cleanup).
    command.downgrade(cfg, "ffcb2b9d04bb")
    conn = sqlite3.connect(str(path))
    try:
        assert not (_NEW_INDEXES & _index_names(conn))
        assert conn.execute("SELECT COUNT(*) FROM favorite_items").fetchone()[0] == 2
    finally:
        conn.close()


def test_tag_response_carries_is_deprecated(client: TestClient) -> None:
    # audit #37: api/tags passes is_deprecated but the schema used to drop it
    # silently (extra='ignore'); it must reach the client now.
    client.post("/api/auth/setup", json={"username": "admin", "password": "pw12345678"})
    created = client.post("/api/tags", json={"name": "aria", "category": "general"})
    assert created.status_code == 201
    assert created.json()["is_deprecated"] is False

    tag_id = created.json()["id"]
    assert client.get(f"/api/tags/{tag_id}").json()["is_deprecated"] is False
    listed = client.get("/api/tags").json()["data"]
    assert listed and all("is_deprecated" in t for t in listed)
