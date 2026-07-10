"""FastAPI application entry point."""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import api_router
from app.config import settings
from app.deps import get_current_session
from app.models.user import Session as SessionRow
from app.services import tasks as task_scheduler
from app.services.errors import (
    AppError,
    NotFoundError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)

# Baseline logging config: app loggers emit key=value domain events (INFO and
# up) to stderr next to uvicorn's request logs. See logging-guidelines.md.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title="Picture Mangers API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Image storage root — created on startup so a fresh dev checkout doesn't
# error before any post is imported.
settings.media_path.mkdir(parents=True, exist_ok=True)

# Files under media/posts/{id}/ are immutable: a post id is never reused and
# its files are never rewritten, so clients may cache them forever.
_MEDIA_CACHE_CONTROL = "public, max-age=31536000, immutable"


@app.get("/media/{path:path}")
def get_media_file(
    path: str,
    _session: SessionRow = Depends(get_current_session),
) -> FileResponse:
    """Serve a stored media file (original/preview/thumb) to a logged-in session.

    Replaces the former unauthenticated StaticFiles mount: the URL shape stays
    /media/<relative path> (the Next.js rewrite depends on it), but the session
    cookie is now required and long-lived caching is enabled. The resolve +
    is_relative_to pair rejects any path escaping the media directory.
    """
    base = settings.media_path.resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise NotFoundError("文件不存在")
    return FileResponse(target, headers={"Cache-Control": _MEDIA_CACHE_CONTROL})


# Unified error envelope: AppError subclasses, request-validation failures
# (422), and a catch-all for unexpected faults.
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# Background task scheduler (APScheduler). Started lazily on first job submit;
# the shutdown hook stops it cleanly so the process can exit. See services/tasks.py.
@app.on_event("shutdown")
def _shutdown_scheduler() -> None:
    task_scheduler.shutdown_scheduler()


@app.get("/")
def root() -> dict:
    return {"name": "Picture Mangers API", "docs": "/docs"}
