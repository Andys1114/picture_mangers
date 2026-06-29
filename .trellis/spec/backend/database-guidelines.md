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
- **Denormalized counters are explicit** — `post_count`, `fav_count` are kept on the parent row to avoid JOIN+COUNT at read time; they are updated by the service that mutates the relation.
- **Association tables** use composite primary keys: `PostTag(post_id, tag_id)`, `FavoriteItem(favorite_id, post_id)`.
- **Foreign keys** specify `ondelete="CASCADE"` so deletes propagate.

## Query Patterns

- **Always go through the ORM / Core** — no raw string SQL, to stay parameterized and injection-safe.
- **`select(...)` 2.0 style** — `db.execute(select(User).where(...)).scalar_one_or_none()`.
- **Reverse lookups need an index** — e.g. `post_tags` has `Index("ix_post_tags_tag_id", "tag_id")` for "all posts with this tag".
- **Recursive CTEs** for graph traversal — used for tag implication expansion (`WITH RECURSIVE ...`).

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
