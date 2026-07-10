# Logging Guidelines

> How logging is done in this project.

---

## Overview

Use Python's stdlib `logging` (no third-party logger yet). The FastAPI/uvicorn
loggers handle request lifecycle. App code logs domain events through a
module-level `logger = logging.getLogger(__name__)`. `app/main.py` sets the
baseline `logging.basicConfig(level=logging.INFO, ...)` so INFO domain events
actually reach stderr next to uvicorn's request logs.

---

## Log Levels

- **DEBUG** — local dev only; e.g. parsed search tokens, generated SQL fragments.
- **INFO** — normal lifecycle: app startup, migration applied, long-task started/finished.
- **WARNING** — recoverable degradation: rate-limit hit + retried, duplicate image skipped, expired session rejected.
- **ERROR** — a request failed unexpectedly; the catch-all handler also logs these.

## Structured Logging

No structured-logging library yet. Until one is added, log with key=value
style so logs are greppable:

```python
logger.info("import task started path=%s total=%d", path, total)
```

Required fields in spirit: what happened, which entity (id), and the
triggering input. Avoid free-form prose.

## What to Log

- Auth: setup completed, login success/failure (username only, not password), logout.
- Long tasks (import/scrape): started, progress milestones, finished (with counts), cancelled, failed.
- Scraping: rate-limit pauses, retries, HTTP errors from upstream.
- Migration: applied revision id.

## What NOT to Log

- **Passwords or password hashes** — never.
- **Full session tokens** — log at most the first 8 chars if correlation is needed.
- **Image bytes / file contents** — never.
- **PII beyond the username** — this is a single-user app, but keep the habit.

## Common Mistakes

### Common Mistake: Alembic silences app loggers

**Symptom**: domain-event logs (and caplog captures in tests) silently vanish after any programmatic `alembic upgrade` — the first test that asserts on logs passes, every later one sees zero records.

**Cause**: `alembic/env.py` calls `logging.config.fileConfig(...)`, whose default `disable_existing_loggers=True` flips every logger already created at that moment (all cached `app.*` module loggers) to `disabled=True`. Tests run `upgrade head` once per test case, so the second test onward is muted.

**Fix / Prevention**: always pass `disable_existing_loggers=False`:

```python
fileConfig(config.config_file_name, disable_existing_loggers=False)
```
