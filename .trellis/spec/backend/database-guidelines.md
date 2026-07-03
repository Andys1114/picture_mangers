# Database Guidelines

> ORM patterns, queries, migrations.

---

## Overview

SQLite + SQLAlchemy 2.0 declarative ORM + Alembic migrations. WAL mode and
foreign keys are enforced on every connection. Schema is owned by Alembic —
`create_all` is never used at runtime.

---

## ORM Conventions

- **Declarative 2.0 style** — `class Base(DeclarativeBase)`, `Mapped[T]` + `mapped_column(...)`.
- **One `__tablename__` per table**, plural (`posts`, `tags`, `post_tags`).
- **Shared mixins** for repeated column groups: `TimestampMixin` (created_at/updated_at with `server_default=func.current_timestamp()`).
- **Denormalized counter `post_count` only** — `Tag.post_count` is kept on the tag row and equals the number of `post_tags` rows for that tag. Because implications are materialized at write time (see ADR-0001), `post_tags` always holds the fully-expanded tag set, so `post_count` is always accurate and needs no lazy recompute / dirty flag. It is bumped by whatever service mutates `post_tags` — currently `services/tags.py:tag_post` and `create_implication` backfill (add-only this slice; the ADR's sticky-delete rule means there is no decrement path yet).
- **No `fav_count`** — favorite counts are **not** tracked. Whether a post was favorited is derived from membership in a `favorite_items` row; there is no `Post.fav_count` column. Do not re-introduce one.
- **Association tables** use composite primary keys: `PostTag(post_id, tag_id)`, `FavoriteItem(favorite_id, post_id)`.
- **Foreign keys** specify `ondelete="CASCADE"` so deletes propagate.

## Query Patterns

- **Always go through the ORM / Core** — no raw string SQL, to stay parameterized and injection-safe.
- **`select(...)` 2.0 style** — `db.execute(select(User).where(...)).scalar_one_or_none()`.
- **Reverse lookups need an index** — e.g. `post_tags` has `Index("ix_post_tags_tag_id", "tag_id")` for "all posts with this tag".
- **Implication closure — write-time only** — a tag's full implication closure (antecedent → consequent, transitively) is computed only at **write time**: when a post is tagged (`services/tags.py:tag_post`, manual or scrape/import) and when an implication is created and existing antecedent posts are backfilled (`services/tags.py:create_implication`). The closure is materialized into `post_tags` so reads never recurse; search is a plain `post_tags` AND match.
- **Closure implementation: BFS with visited-set, not a recursive CTE** — the closure is computed by an application-layer BFS over the `tag_implications` adjacency (visited set guards against pre-existing cycles). A recursive CTE was the original spec preference, but SQLAlchemy 2.0's recursive-CTE construction on SQLite is finicky enough that the BFS form is clearer and semantically equivalent for single-user scale. If a future scale demands it, a recursive CTE can replace the BFS without changing any caller.
- **Implication cycle prevention** — before inserting a new implication `A→B`, `services/tags.py` runs a reverse-reachability check ("can B already reach A?") via the same closure BFS. If yes, the new edge would form a cycle → reject with `ConflictError` (409). Self-loops (`A→A`) are also rejected. The visited-set in the BFS is the belt-and-suspenders guard against any pre-existing cycle. See ADR-0001.
- **`post_count` maintained at write time** — `Tag.post_count` is bumped by whatever service mutates `post_tags`: `tag_post` (+1 on add, slice 2), `create_implication` backfill (+1, slice 2), and `post_edit.update_post` (−1 on full-replace remove, slice 6 backend). It always equals the number of `post_tags` rows for that tag; no lazy recompute. Tag/implication deletion is still absent (ADR-0001 "sticky delete"); the `post_edit` decrement only removes a tag from one post, never retracts an implication.

## Duplicate Images (Post)

- **Two-stage dedup** — on import, compute `md5` first; if an existing post has the same `md5`, the ingest raises `DuplicateError` (exact duplicate, no row created). `phash` (perceptual hash) is split across two phases: the **hash value is computed synchronously and stored** on the Post row during ingest (`services/media.py:ingest`); the **near-neighbor lookup** that would set `is_duplicate`/`duplicate_of_id` runs **asynchronously** after import (a later slice's scheduler). So an ingested post always has `phash` set but leaves `is_duplicate=False` and `duplicate_of_id=None` until the async pass marks it.
- **`duplicate_of_id`** — a self-referencing nullable FK on `Post` (`ForeignKey("posts.id", ondelete="SET NULL")`) pointing at the chosen original. The boolean `is_duplicate` is a fast-filter convenience; the authoritative signal is `duplicate_of_id IS NOT NULL`.
- **Hidden by default** — duplicates are hidden from the gallery main view (they have a dedicated view) but may still be added to favorites.
- **md5 exact dedup shipped** — `services/media.py:ingest` implements the md5-skip stage (raises `DuplicateError`, code `duplicate`, HTTP 409). The phash neighbor-lookup + `duplicate_of_id` assignment + search dedup-filter still land in later slices.

- **`scan_history` table (slice 8)** — migration `ffcb2b9d04bb` adds `scan_history(id, path unique, mtime, scanned_at)` to track locally-imported files for incremental re-scans (skip unchanged files by mtime without re-reading bytes). Reversible (`downgrade -1` drops the table). The model is in `app/models/scan_history.py`.
- **Background-task DB sessions are independent** — worker threads (APScheduler `BackgroundScheduler`) create their own `SessionLocal()`; never share a request's session across threads (SQLAlchemy sessions aren't thread-safe). Each file/step commits so progress persists and transactions stay short.

## Scrape Dedup (Source)

- **`(source_site, source_id)` partial unique index** — for non-null sources, a partial unique index on `Post(source_site, source_id)` prevents the same site+id from being imported twice, even under concurrent scrapes.
- **Two-stage scrape dedup** — (1) at the scrape-list stage, query existing `(source_site, source_id)` pairs and skip already-imported posts (no download needed). (2) After download, compute `md5`; if it already exists (same image, different site or changed id), route through the duplicate-image flow above rather than creating a new primary post.
- **Single source per post** — a post records only the **first** source it was scraped from. A later scrape of the same content from another site does not overwrite `source_*` fields and does not create a second primary post. Multi-source association is out of scope.

## Migrations (Alembic)

- **Schema lives in migrations, not `create_all`** — lets later subtasks evolve the schema additively.
- **`alembic/env.py` injects the DB URL** from `app.config` at runtime; `alembic.ini`'s `sqlalchemy.url` is left blank. Do NOT hardcode a URL in the ini.
- **`render_as_batch=True`** is set in `env.py` so SQLite ALTER TABLE works (batch mode).
- **Migration engine applies the same pragmas** (WAL, foreign_keys) as runtime, via a `connect` event listener.
- **autogenerate flow**: `python -m alembic revision --autogenerate -m "..."` then review the generated file (check tables/indexes/constraints) before committing.

## SQLite Pragmas (set on every connection)

```python
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()
```

Both `app/db.py` (runtime) and `alembic/env.py` (migrations) set these.

## Encoding Gotcha

`alembic.ini` is read with `encoding="locale"` (GBK on this Windows machine).
**Do not put non-ASCII characters in `alembic.ini` comments** — they will raise
`UnicodeDecodeError`. Python files (env.py, models) are UTF-8 and may contain
non-ASCII freely, but prefer English for code comments.

---

## Examples

- Eight-table initial schema: `alembic/versions/f3d99311f0cf_initial_schema.py`.
- Connection pragmas: `app/db.py` and `alembic/env.py`.
- Implication materialization decision (write-time closure, not read-time recursion): `docs/adr/0001-implication-materialized-at-write-time.md`.
