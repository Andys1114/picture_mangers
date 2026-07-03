# Directory Structure

> How backend code is organized in this project.

---

## Overview

The backend is a single FastAPI app under `backend/`. Code is layered: API routes
parse HTTP and delegate to services; services hold business logic; models are
pure ORM; schemas are Pydantic request/response shapes; deps hold cross-cutting
FastAPI dependencies.

---

## Directory Layout

```
backend/
├── app/
│   ├── main.py              FastAPI app entry: middleware + router + error handlers
│   ├── config.py            Settings (pydantic-settings, .env-driven)
│   ├── db.py                engine, SessionLocal, get_db dependency, WAL/FK pragmas
│   ├── deps.py              cross-cutting deps (get_current_user)
│   ├── models/              SQLAlchemy ORM (one file per aggregate, __init__ exports all)
│   ├── schemas/             Pydantic request/response models
│   ├── api/                 route modules; __init__ aggregates into api_router (/api prefix). Implemented: auth, health, posts, tags.
│   └── services/            business logic. Implemented: auth, errors, search, media, tags. Future: scraper.
├── alembic/                 migrations; env.py injects runtime URL + pragmas
├── alembic.ini              URL left blank — injected by env.py from app.config
├── tests/                   pytest; conftest provides tmp DB + migrated TestClient
├── media/                   image storage (gitignored)
├── pyproject.toml           primary deps
└── requirements.txt         pinned for reproducible installs
```

---

## Module Organization

- **One file per aggregate in `models/`** — `user.py` (User + Session), `post.py` (Post), `tag.py` (Tag + PostTag + TagImplication), `favorite.py` (Favorite + FavoriteItem). `models/__init__.py` imports every model so Alembic autogenerate sees the full schema.
- **`api/__init__.py` aggregates routers** — each route module exposes a `router`; `__init__` mounts them under a single `APIRouter(prefix="/api")`. `main.py` only calls `app.include_router(api_router)`.
- **Routes stay thin** — parse request, call a service function, return a schema. No business logic in `api/`.
- **Services are reusable** — e.g. `auth.create_session` is called by both `/setup` and `/login`.

---

## Naming Conventions

- Packages/modules: `snake_case`.
- Files: `snake_case.py`.
- ORM classes: `PascalCase`, `__tablename__` plural (`posts`, `tags`, `post_tags`).
- Schemas: `<Verb>Request` / `<Entity>Response` (e.g. `SetupRequest`, `UserResponse`).
- Route modules named after the resource: `auth.py`, `health.py`, `posts.py`, `tags.py` (implemented).



## Examples

- Clean layered route: `app/api/auth.py` (thin handlers delegating to `app/services/auth.py`).
- Media ingestion kernel (no route — pure service): `app/services/media.py` (`ingest` + md5/phash/thumbnails).
- Engine + pragmas + dependency: `app/db.py`.
- Model aggregate with association tables: `app/models/tag.py` (Tag + PostTag + TagImplication).
