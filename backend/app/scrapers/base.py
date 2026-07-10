"""Scraper abstract base + shared data classes.

A scraper adapter is site-specific (Danbooru, Gelbooru, ...). It owns:
- API URL construction + JSON parsing for its site,
- rate limiting (polite crawl),
- retry with exponential backoff on transient failures.

It does NOT own DB writes or tag materialization — that orchestration lives in
``app/services/scrape.py`` so a scraper stays a pure upstream-data adapter.
``download`` is a concrete default here (validated, size-capped streaming GET)
since it's the same for every HTTP-based image board; subclasses override only
if a site needs auth headers or referrer tricks.
"""
from __future__ import annotations

import abc
import time
from contextlib import AbstractContextManager
from urllib.parse import urljoin, urlparse

import httpx

from app.services.errors import ScraperError

# Hard cap on a single downloaded image. Kept in sync with the local-import
# cap (``services/import_service.py`` MAX_FILE_BYTES, 200 MB) but duplicated
# here so the scraper layer doesn't depend on service-internal constants.
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024

# How many redirect hops ``download`` follows manually. Each hop is
# re-validated (https + allowed_hosts) before the next request is sent.
MAX_REDIRECTS = 3


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

    # Host whitelist for ``download``: exact hostnames or ``*.domain``
    # wildcards (matching the bare domain and any subdomain). Image URLs come
    # from untrusted upstream JSON, so the empty default rejects everything —
    # concrete scrapers must declare the hosts they may fetch from.
    allowed_hosts: tuple[str, ...] = ()

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

        ``image_url`` is upstream-controlled, so every hop must be https on an
        ``allowed_hosts`` host: redirects are followed manually (at most
        ``MAX_REDIRECTS``) with per-hop re-validation, and the body is streamed
        with a ``MAX_DOWNLOAD_BYTES`` cap instead of read in one piece.
        Subclasses override for site-specific transport requirements.
        """
        url = image_url
        try:
            for _hop in range(MAX_REDIRECTS + 1):
                self._validate_download_url(url)
                with open_stream(url) as resp:
                    if resp.has_redirect_location:
                        # ``has_redirect_location`` (unlike ``is_redirect``,
                        # which is True for *any* 3xx on httpx>=0.28) guarantees
                        # a Location header exists; urljoin resolves relative
                        # redirects against ``url``. A 3xx without Location
                        # falls through to raise_for_status below.
                        url = urljoin(url, resp.headers["location"])
                        continue
                    resp.raise_for_status()
                    received = 0
                    chunks: list[bytes] = []
                    for chunk in resp.iter_bytes():
                        received += len(chunk)
                        if received > MAX_DOWNLOAD_BYTES:
                            raise ScraperError(f"图片超过下载大小上限: {image_url}")
                        chunks.append(chunk)
                    return b"".join(chunks)
        except httpx.HTTPError as exc:
            raise ScraperError(f"下载图片失败: {image_url}") from exc
        raise ScraperError(f"重定向次数过多: {image_url}")

    def _validate_download_url(self, url: str) -> None:
        """Reject ``url`` unless it is https and its host is whitelisted."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ScraperError(f"下载地址必须为 https: {url}")
        host = (parsed.hostname or "").lower()
        if not self._host_allowed(host):
            raise ScraperError(f"下载地址主机不在白名单: {url}")

    def _host_allowed(self, host: str) -> bool:
        """True if ``host`` matches ``allowed_hosts`` (exact or ``*.`` wildcard)."""
        for pattern in self.allowed_hosts:
            if pattern.startswith("*."):
                if host == pattern[2:] or host.endswith(pattern[1:]):
                    return True
            elif host == pattern:
                return True
        return False


def open_stream(url: str) -> AbstractContextManager[httpx.Response]:
    """Open a streaming GET for ``url`` without following redirects (the
    caller validates and follows them manually). Thin wrapper so tests can
    substitute an ``httpx.MockTransport``-backed client without real network
    (same pattern as ``rate_limit_sleep`` below)."""
    return httpx.stream("GET", url, timeout=30.0, follow_redirects=False)


def rate_limit_sleep(seconds: float) -> None:
    """Thin wrapper around ``time.sleep`` so tests can patch rate-limiting
    without actually sleeping (tests monkeypatch ``scrapers.base.rate_limit_sleep``
    or the scraper's own sleep method)."""
    time.sleep(seconds)
