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
- **Denormalized counter `post_count` only** — `Tag.post_count` is kept on the tag row and equals the number of `post_tags` rows for that tag. Because implications are materialized at write time (see ADR-0001), `post_tags` always holds the fully-expanded tag set, so `post_count` is always accurate and needs no lazy recompute / dirty flag. It is bumped (±1) by whatever service mutates `post_tags` (tag add/remove, implication backfill).
- **No `fav_count`** — favorite counts are **not** tracked. Whether a post was favorited is derived from membership in a `favorite_items` row; there is no `Post.fav_count` column. Do not re-introduce one.
- **Association tables** use composite primary keys: `PostTag(post_id, tag_id)`, `FavoriteItem(favorite_id, post_id)`.
- **Foreign keys** specify `ondelete="CASCADE"` so deletes propagate.

## Query Patterns

- **Always go through the ORM / Core** — no raw string SQL, to stay parameterized and injection-safe.
- **`select(...)` 2.0 style** — `db.execute(select(User).where(...)).scalar_one_or_none()`.
- **Reverse lookups need an index** — e.g. `post_tags` has `Index("ix_post_tags_tag_id", "tag_id")` for "all posts with this tag".
- **Recursive CTEs for implication closure — write-time only** — `WITH RECURSIVE ...` is used to compute a tag's full implication closure (antecedent → consequent, transitively) at **write time**: when a post is tagged (manual or scrape/import) and when an implication is created/changed and existing antecedent posts are backfilled. The closure is materialized into `post_tags` so reads never recurse. Search is a plain `post_tags` AND match.
- **Implication cycle prevention** — before inserting a new implication `A→B`, run a reverse-reachability check ("can B already reach A?"). If yes, the new edge would form a cycle → reject with `ConflictError` (409). The closure computation itself also carries a visited-set guard as a belt-and-suspenders against any pre-existing cycle. See ADR-0001.

## Duplicate Images (Post)

- **Two-stage dedup** — on import, compute `md5` first; if an existing post has the same `md5`, skip entirely (exact duplicate, no row created). `phash` (perceptual hash) is computed **asynchronously** after import; near-matches mark the new post as a duplicate.
- **`duplicate_of_id`** — a self-referencing nullable FK on `Post` (`ForeignKey("posts.id", ondelete="SET NULL")`) pointing at the chosen original. The boolean `is_duplicate` is a fast-filter convenience; the authoritative signal is `duplicate_of_id IS NOT NULL`.
- **Hidden by default** — duplicates are hidden from the gallery main view (they have a dedicated view) but may still be added to favorites.
- **Pending model change** — `Post.duplicate_of_id` does not yet exist in the initial schema migration; a later subtask adds it via a new Alembic migration. `Post.fav_count` (present in the initial schema) is to be **dropped** by that same later migration.

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
