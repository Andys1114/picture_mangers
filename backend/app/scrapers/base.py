"""Scraper abstract base + shared data classes.

A scraper adapter is site-specific (Danbooru, Gelbooru, ...). It owns:
- API URL construction + JSON parsing for its site,
- rate limiting (polite crawl),
- retry with exponential backoff on transient failures.

It does NOT own DB writes or tag materialization — that orchestration lives in
``app/services/scrape.py`` so a scraper stays a pure upstream-data adapter.
``download`` is a concrete default here (plain httpx GET) since it's the same
for every HTTP-based image board; subclasses override only if a site needs
auth headers or referrer tricks.
"""
from __future__ import annotations

import abc
import time

import httpx

from app.services.errors import ScraperError


class ScrapedTag:
    """A tag scraped from an upstream site, with its category.

    ``category`` uses the project's five-bucket scheme
    (general/character/copyright/artist/meta) so it maps directly onto
    ``Tag.category`` without translation.
    """

    __slots__ = ("name", "category")

    def __init__(self, name: str, category: str) -> None:
        self.name = name
        self.category = category

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"ScrapedTag(name={self.name!r}, category={self.category!r})"


class ScrapedPost:
    """A post scraped from an upstream site, ready to hand to the orchestrator.

    ``source_id`` is a str for cross-site uniformity (Danbooru ids are ints,
    other sites may use strings). The orchestrator pairs ``source_site`` (from
    the scraper) with ``source_id`` for the partial-unique-index dedup.
    """

    __slots__ = ("source_id", "image_url", "tags", "rating", "source_url", "file_ext", "is_animated")

    def __init__(
        self,
        *,
        source_id: str,
        image_url: str,
        tags: list[ScrapedTag],
        rating: str,
        source_url: str,
        file_ext: str,
        is_animated: bool,
    ) -> None:
        self.source_id = source_id
        self.image_url = image_url
        self.tags = tags
        self.rating = rating
        self.source_url = source_url
        self.file_ext = file_ext
        self.is_animated = is_animated

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"ScrapedPost(source_id={self.source_id!r}, rating={self.rating!r}, {len(self.tags)} tags)"


class Scraper(abc.ABC):
    """Site-agnostic scraper interface.

    Subclasses set ``source_site`` (matches ``Post.source_site``) and implement
    ``search`` / ``fetch``. ``download`` has a concrete default; override only
    for site-specific transport (auth, referrer).
    """

    source_site: str = ""

    @abc.abstractmethod
    def search(self, query: str, *, page: int = 1, limit: int = 100) -> list[ScrapedPost]:
        """Return posts matching ``query`` (tag string) at the given page."""
        raise NotImplementedError

    @abc.abstractmethod
    def fetch(self, source_id: str) -> ScrapedPost:
        """Return a single post by its upstream id."""
        raise NotImplementedError

    def download(self, image_url: str) -> bytes:
        """Download raw image bytes from ``image_url``.

        Default implementation: plain httpx GET with a reasonable timeout.
        Subclasses override for site-specific transport requirements.
        """
        try:
            resp = httpx.get(image_url, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ScraperError(f"下载图片失败: {image_url}") from exc
        return resp.content


def rate_limit_sleep(seconds: float) -> None:
    """Thin wrapper around ``time.sleep`` so tests can patch rate-limiting
    without actually sleeping (tests monkeypatch ``scrapers.base.rate_limit_sleep``
    or the scraper's own sleep method)."""
    time.sleep(seconds)
