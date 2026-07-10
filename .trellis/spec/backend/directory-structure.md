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
│   ├── main.py              FastAPI app entry: middleware + router + error handlers + authenticated /media file route
│   ├── config.py            Settings (pydantic-settings, .env-driven)
│   ├── db.py                engine, SessionLocal, get_db dependency, WAL/FK/busy_timeout pragmas
│   ├── deps.py              cross-cutting deps (get_current_user, get_current_session)
│   ├── models/              SQLAlchemy ORM (one file per aggregate, __init__ exports all)
│   ├── schemas/             Pydantic request/response models
│   ├── api/                 route modules; __init__ aggregates into api_router (/api prefix). Implemented: auth, health, posts, tags, favorites, import_.
│   ├── services/            business logic. Implemented: auth, errors, search, media, tags, scrape, favorites, post_edit, tasks, import_service.
│   ├── scrapers/            site-specific upstream adapters (pure HTTP, no DB/FastAPI). Implemented: base (Scraper ABC + ScrapedPost), danbooru. Future: gelbooru/moebooru.
│   └── models/  ...scan_history.py (local-import incremental scan tracking)
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
- **Media files are served by an authenticated route, not StaticFiles** — `GET /media/{path:path}` in `main.py`: `Depends(get_current_session)`, `resolve()` + `is_relative_to(media_path)` traversal guard (404 on escape), `FileResponse` with `Cache-Control: public, max-age=31536000, immutable` (files under `posts/{id}/` are immutable; ids are never reused). A bare `StaticFiles` mount bypasses auth entirely — don't reintroduce one (audit #5/#17). URL shape stays `/media/<relative path>`; the Next.js rewrite depends on it.
- **Session-row model import alias** — `from app.models.user import Session as SessionRow`. Importing it bare shadows `sqlalchemy.orm.Session` and silently mistypes every `db: Session` annotation in the file (audit #40).

---

## Naming Conventions

- Packages/modules: `snake_case`.
- Files: `snake_case.py`.
- ORM classes: `PascalCase`, `__tablename__` plural (`posts`, `tags`, `post_tags`).
- Schemas: `<Verb>Request` / `<Entity>Response` (e.g. `SetupRequest`, `UserResponse`).
- Route modules named after the resource: `auth.py`, `health.py`, `posts.py`, `tags.py`, `favorites.py`, `import_.py` (trailing underscore avoids the `import` keyword) (implemented).



## Examples

- Clean layered route: `app/api/auth.py` (thin handlers delegating to `app/services/auth.py`).
- Media ingestion kernel (no route — pure service): `app/services/media.py` (`ingest` + md5/phash/thumbnails).
- Scraper adapter + orchestration split: `app/scrapers/danbooru.py` (pure HTTP: search/fetch/download, rate-limit, retry) vs `app/services/scrape.py` (DB glue: download→`media.ingest`→`tags.tag_post`, two-stage dedup). Scraper knows nothing about DB; orchestrator knows nothing about HTTP specifics.
- Engine + pragmas + dependency: `app/db.py`.
- Model aggregate with association tables: `app/models/tag.py` (Tag + PostTag + TagImplication).
