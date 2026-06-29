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
- **Returning `str(exc)` / stack traces to clients** — use the error envelope.

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
