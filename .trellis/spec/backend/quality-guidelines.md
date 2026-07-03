# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend code is type-checked Python 3.11+. Quality bars: layered structure,
ORM-only data access, parameterized queries, tests covering every AC. No
business logic in route handlers.

---

## Forbidden Patterns

- **`Base.metadata.create_all()` at runtime** — schema is owned by Alembic. Use `alembic upgrade head`. (See database-guidelines.)
- **Raw string SQL with interpolation** — `f"SELECT ... WHERE name='{x}'"` is banned. Always ORM/Core with bound params.
- **Business logic in `api/` route handlers** — routes parse + delegate to `services/`. If a route grows logic, move it to a service.
- **Non-ASCII in `alembic.ini`** — read with locale encoding (GBK here); will crash. English only in that file.
- **`except: pass` / bare `except`** — either handle + log, or let it propagate to the global handler.
- **Storing passwords in plaintext or weak hashes** — bcrypt cost=12 only.
- **Re-introducing `Post.fav_count`** — favorite counts are not tracked (grilling decision). Derive favorited state from `favorite_items` membership instead.
- **Read-time recursive CTE for search** — implications are materialized at write time (ADR-0001); search is a plain `post_tags` AND match.
- **Returning `str(exc)` / stack traces to clients** — use the error envelope.

## Search & Display Semantics

- **Search is AND-only this milestone** — query syntax is multiple tags space-separated = AND over `post_tags`. `NOT` (`-tag`), `OR` (`~tag1 ~tag2`), and wildcard (`tag1*`) are **out of scope this milestone** (deferred to a later version). Do not implement them yet; do not write tests assuming they exist.
- **Search runs on materialized `post_tags`** — because implications are materialized at write time (ADR-0001), search is a plain `post_tags` AND match. No recursive CTE at read time.
- **Default sort** — by `created_at` / `id` descending (newest first). No popularity sort (no favorite-count field exists).
- **Rating filter** — `Post.rating` is one of `safe` | `questionable` | `explicit` (default `safe`). The gallery main view and search default to `safe`-only; the caller may explicitly request `questionable` / `explicit` / all. Treat rating as an implicit filter layered on top of the tag query.
- **Duplicates hidden by default** — posts with `duplicate_of_id IS NOT NULL` are excluded from the gallery main view and from search results unless the caller explicitly requests the duplicates view.

## Domain Field Contract

The initial schema migration (`f3d99311f0cf`) predates several grilling decisions. Migration `74035bafb648` ships the alignment:
- Drops `Post.fav_count` (favorite counts are not tracked).
- Adds `Post.duplicate_of_id` (self-FK, `ondelete="SET NULL"`, nullable).
- Adds a partial unique index `ix_posts_source_site_source_id` on `Post(source_site, source_id)` for non-null sources (`sqlite_where` predicate).

The migration is hand-written (not autogenerate) because Alembic cannot reliably detect a partial index's WHERE predicate; it is fully reversible (`downgrade -1`). The model mirrors this in `app/models/post.py`. The business logic that *consumes* these fields is landing incrementally: the **md5 exact-dedup stage** ships in `services/media.py:ingest` (raises `DuplicateError`, code `duplicate`); the **phash neighbor-lookup + `duplicate_of_id` assignment** and **scrape-list source dedup** still land in later slices.

## Required Patterns

- **Type hints on all function signatures** — `def f(x: int) -> str:`. Use `T | None` (3.11+ union) over `Optional[T]`.
- **`from __future__ import annotations`** at the top of every module.
- **Pydantic schemas for every request and response** — no raw dicts across the API boundary.
- **`Mapped[T]` + `mapped_column(...)`** for ORM columns (2.0 style).
- **`get_db` dependency** for DB access in routes — never instantiate `SessionLocal()` in a route.
- **Custom `AppError` subclasses** for expected failures; let the global handler format them.

## Testing Requirements

- **Every AC in `prd.md` has at least one test.** Test names mirror the AC (`test_<behavior>`).
- **Tests use the `client` fixture** (tmp DB + migrated schema), never the real `picture_mangers.db`.
- **`pytest -v` must be green** before a subtask is reported done.
- **Run from `backend/`** so `pyproject.toml` config (testpaths, pythonpath) applies.
- Prefer parametrized tests for state-machine coverage (e.g. auth branches).

## Code Review Checklist

- [ ] Layering intact (no logic in routes, no HTTP in services).
- [ ] No `create_all`; schema changes ship as a reviewed Alembic migration.
- [ ] All queries parameterized (ORM/Core).
- [ ] New error cases raise an `AppError` subclass with a stable `code`.
- [ ] Type hints + `from __future__ import annotations` present.
- [ ] ACs covered by tests; `pytest -v` green.
- [ ] No secrets/passwords/tokens logged.
- [ ] No non-ASCII in `alembic.ini`.
- [ ] Search is AND-only over `post_tags` (no read-time recursion); rating/duplicate filters applied.
- [ ] No `fav_count` field or favorite-count logic introduced.
- [ ] **Docstrings/comments match the latest ADR** — when an ADR supersedes a design (e.g. ADR-0001 replaces read-time recursion with write-time materialization), no surviving docstring still describes the superseded behavior. Grep the affected terms after landing an ADR change.
