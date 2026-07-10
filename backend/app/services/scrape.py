"""Scrape→ingest orchestration: download, dedup, ingest, materialize tags.

This is the cross-layer glue between a ``Scraper`` adapter (upstream data +
bytes) and the already-shipped ingestion/materialization kernels:
``services/media.py:ingest`` (slice 3) and ``services/tags.py:tag_post`` /
``create_implication`` (slice 2 remainder). It owns no route, no scheduler —
those land in slice 8 (the import page).

Two-stage dedup (``database-guidelines.md``「Scrape Dedup」):
1. **Source dedup at list stage** — before downloading, skip a scraped post
   whose ``(source_site, source_id)`` already exists (no bytes fetched).
2. **md5 dedup at ingest stage** — after download, ``media.ingest`` raises
   ``DuplicateError`` if the bytes match an existing post (same image under a
   different source, or a changed upstream id). Counted as duplicate, not failed.

Per-post error isolation: a single download/parse failure is counted as
``failed`` and the batch continues; only ``DuplicateError`` is a recognized
duplicate signal, everything else is a real failure.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.post import Post
from app.scrapers.base import Scraper, ScrapedPost
from app.services import media, tags
from app.services.errors import ConflictError, DuplicateError

if TYPE_CHECKING:
    from app.services.tasks import TaskState

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Outcome counters for a scrape batch."""

    new: int = 0
    duplicate: int = 0
    failed: int = 0


def scrape_to_db(
    db: Session,
    scraper: Scraper,
    query: str,
    *,
    limit: int = 20,
    state: "TaskState | None" = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> ScrapeResult:
    """Search ``query`` via ``scraper``, download + ingest each post, tag it.

    Returns a ``ScrapeResult`` with new/duplicate/failed counts. Each post is
    processed independently — one failure never aborts the batch.

    ``state`` and ``is_cancelled`` are optional task-integration hooks (both
    default to None so direct callers keep the old signature): ``state.total``
    is set once the search returns and ``state.processed`` advances per post;
    ``is_cancelled`` is polled before each post — True stops the batch and
    returns the counts so far.
    """
    result = ScrapeResult()
    posts = scraper.search(query, limit=limit)
    if state is not None:
        state.total = len(posts)

    for sp in posts:
        if is_cancelled is not None and is_cancelled():
            return result

        try:
            # Stage 1: source dedup — skip if (source_site, source_id) already imported.
            existing = db.execute(
                select(Post.id).where(
                    Post.source_site == scraper.source_site,
                    Post.source_id == sp.source_id,
                )
            ).first()
            if existing is not None:
                result.duplicate += 1
                continue

            # Download the image bytes.
            try:
                data = scraper.download(sp.image_url)
            except Exception as exc:
                logger.warning("scrape download failed source_id=%s err=%s", sp.source_id, exc)
                db.rollback()
                result.failed += 1
                continue

            # Stage 2: ingest (md5 dedup raises DuplicateError; source partial
            # unique index also enforces source dedup at the DB level as a
            # belt-and-suspenders against races).
            try:
                post = media.ingest(
                    db, data,
                    source_site=scraper.source_site,
                    source_id=sp.source_id,
                    source_url=sp.source_url,
                    file_ext=sp.file_ext,
                    is_animated=sp.is_animated,
                    rating=sp.rating,
                )
            except DuplicateError:
                db.rollback()
                result.duplicate += 1
                continue
            except Exception as exc:
                # Discard any half-flushed Post so it cannot ride along with a
                # later post's commit.
                logger.warning("scrape ingest failed source_id=%s err=%s", sp.source_id, exc)
                db.rollback()
                result.failed += 1
                continue

            # Materialize the scraped tags onto the new post (closure + post_count
            # handled by tag_post).
            try:
                tags.tag_post(db, post.id, [t.name for t in sp.tags])
            except Exception as exc:
                # The post was ingested but tagging failed — count as failed but
                # the post still exists (partial ingest; acceptable, user can
                # re-tag via the future edit endpoint).
                logger.warning(
                    "scrape tagging failed source_id=%s post_id=%s err=%s",
                    sp.source_id, post.id, exc,
                )
                db.rollback()
                result.failed += 1
                continue

            result.new += 1
        finally:
            if state is not None:
                state.processed += 1

    return result


def bootstrap_implications(db: Session, scraper: Scraper) -> int:
    """Pull the upstream implication graph and seed it locally.

    For each (antecedent_name, consequent_name) pair from the scraper, get-or-
    create both tags then call ``tags.create_implication`` (which dedupes,
    cycle-checks with 409, and backfills existing posts). Cycles are skipped
    without aborting — a remote graph may contain edges that, combined with
    locally-added ones, would form a cycle.
    """
    pairs = scraper.fetch_implications()
    created = 0
    for ant_name, con_name in pairs:
        ant = tags.create_tag(db, ant_name) if not _tag_exists(db, ant_name) else _get_tag_by_name(db, ant_name)
        con = tags.create_tag(db, con_name) if not _tag_exists(db, con_name) else _get_tag_by_name(db, con_name)
        try:
            tags.create_implication(db, ant.id, con.id)
            created += 1
        except ConflictError:
            # Cycle or duplicate — skip, don't abort.
            continue
    return created


def _tag_exists(db: Session, name: str) -> bool:
    from app.models.tag import Tag
    return db.execute(select(Tag.id).where(Tag.name == name)).first() is not None


def _get_tag_by_name(db: Session, name: str):
    from app.models.tag import Tag
    return db.execute(select(Tag).where(Tag.name == name)).scalar_one()
