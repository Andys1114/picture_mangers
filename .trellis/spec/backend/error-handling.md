# Error Handling

> How errors are handled in this project.

---

## Overview

Errors flow through custom `AppError` subclasses. Routes raise them (directly
or via deps); global exception handlers convert every error — known and
unexpected — into the unified JSON envelope. Clients never see a raw stack
trace.

---

## Error Types

Defined in `app/services/errors.py`:

- `AppError` — base. Carries `status_code` (default 400), `code` (default `"error"`), and a user-facing `message`.
- `UnauthorizedError` — 401, code `"unauthorized"`.
- `ConflictError` — 409, code `"conflict"`.
- `NotFoundError` — 404, code `"not_found"`. Raised when a referenced resource (e.g. a post id) does not exist.
- `DuplicateError` — 409, code `"duplicate"`. Raised by `services/media.ingest` when an incoming image's md5 already exists; the caller decides whether to skip silently, log, or count it.
- `ScraperError` — 502, code `"scraper_error"`. Raised by scraper adapters (`app/scrapers/`) after rate-limited retries are exhausted (network failure, persistent 5xx, malformed response). The orchestration service (`services/scrape.py`) catches it per-post to isolate failures without aborting the batch.

Add a new subclass when a new HTTP semantics is needed. For a one-off error, raise `AppError(msg, status_code=..., code=...)` inline.

## Error Handling Patterns

- **Raise, don't return error codes** — services and deps raise `AppError` subclasses; routes do not wrap in try/except unless they add context.
- **Deps raise on auth failure** — `get_current_user` raises `UnauthorizedError`; routes just declare the dependency.
- **Let handlers do the formatting** — `app_error_handler` produces the envelope; `unhandled_exception_handler` catches anything else as a 500.

## API Error Responses

Every non-2xx response uses this shape:

```json
{"error": {"code": "unauthorized", "message": "未登录或会话已过期"}}
```

- `code` — machine-readable, snake_case, stable across releases.
- `message` — human-readable, may be Chinese (user-facing).
- HTTP status matches the error's `status_code`.

Wired in `app/main.py` — three handlers, one shape:
```python
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
```

- `RequestValidationError` (FastAPI 422) → `{"error": {"code": "validation_error", "message": <readable, field-prefixed summary>}}`, status 422. Without this handler FastAPI returns `{"detail": [...]}` which the frontend's envelope parser can't read (audit #16).
- `Exception` catch-all → 500 `{"error": {"code": "internal_error", "message": "服务器内部错误"}}` and `logger.exception(...)` server-side.

## Common Mistakes

- **Returning 500 for expected errors** — if a route can anticipate a failure (bad input, missing resource, conflict), raise the right `AppError` subclass, not a bare `Exception`.
- **Leaking stack traces** — never return `str(exc)` to the client; the catch-all returns a generic message. This includes *indirect* channels: a background task's `state.error` flows into `GET /api/tasks/{id}` — store a generic message there ("导入失败，请查看服务器日志") and `logger.exception` the original (audit #36).
- **Swallowing errors silently** — services must not `except: pass`. Either handle and log, or let it propagate to the handler. Per-item worker loops count *and* log each failure (`logger.warning` with path / source_id), and must roll back the session first — see database-guidelines.md "transaction ownership".
