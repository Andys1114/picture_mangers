"""Custom exceptions and the unified error envelope converter."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base app error carrying an HTTP status, code, and user-facing message."""

    status_code: int = 400
    code: str = "error"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(message)


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class NotFoundError(AppError):
    """404 — a referenced resource does not exist."""

    status_code = 404
    code = "not_found"


class DuplicateError(AppError):
    """409 — an exact duplicate (same md5) was rejected at ingest.

    Raised by the media pipeline when an incoming image's md5 already exists.
    The caller (scraper/import) decides whether to skip silently, log, or count
    it as a duplicate hit — the service itself never silently swallows it.
    See ``database-guidelines.md``「Duplicate Images」(md5 exact dedup).
    """

    status_code = 409
    code = "duplicate"


class ScraperError(AppError):
    """502 — a scraper adapter exhausted its retries or hit an unrecoverable
    upstream error (network failure, persistent 5xx, malformed response).

    Raised by scraper adapters (``app/scrapers/``) after rate-limited retries
    are exhausted. The orchestration service (``services/scrape.py``) catches
    it per-post to isolate failures without aborting the whole batch.
    """

    status_code = 502
    code = "scraper_error"


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so clients always get the envelope, never a raw 500 stack trace."""
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "服务器内部错误"}},
    )
