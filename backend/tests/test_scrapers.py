"""Scraper download hardening + packaging/config regressions.

``Scraper.download`` treats upstream-provided image URLs as untrusted: only
https URLs on the scraper's ``allowed_hosts`` whitelist are fetched, redirects
are followed manually with per-hop re-validation, and bodies are streamed
under a hard size cap. All HTTP here goes through ``httpx.MockTransport``
(swapped in for ``scrapers.base.open_stream``) — no real network.
"""
from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.scrapers import base as base_mod
from app.scrapers import danbooru as danbooru_mod
from app.scrapers.danbooru import DanbooruScraper
from app.services.errors import ScraperError


# --- helpers -----------------------------------------------------------------

def _install_transport(monkeypatch, handler) -> list[str]:
    """Route ``base.open_stream`` through an ``httpx.MockTransport`` so
    ``download`` exercises real httpx Response semantics without network.
    Returns the list of request URLs actually sent."""
    calls: list[str] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return handler(request)

    mock_client = httpx.Client(
        transport=httpx.MockTransport(recording_handler), follow_redirects=False
    )

    def open_stream(url: str):
        return mock_client.stream("GET", url, timeout=30.0)

    monkeypatch.setattr(base_mod, "open_stream", open_stream)
    return calls


@pytest.fixture()
def scraper() -> DanbooruScraper:
    return DanbooruScraper(rate_limit_s=0, max_retries=0)


# --- download URL validation (audit #24) ---------------------------------------

def test_download_rejects_non_https_url(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #24
    calls = _install_transport(monkeypatch, lambda _req: httpx.Response(200, content=b"x"))
    with pytest.raises(ScraperError):
        scraper.download("http://cdn.donmai.us/a.png")
    assert calls == [], "non-https must be rejected before any request is sent"


def test_download_rejects_host_outside_whitelist(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #24
    calls = _install_transport(monkeypatch, lambda _req: httpx.Response(200, content=b"x"))
    for url in ("https://evil.example.com/a.png", "https://169.254.169.254/latest/meta-data"):
        with pytest.raises(ScraperError):
            scraper.download(url)
    assert calls == [], "non-whitelisted hosts must never be contacted"


def test_download_follows_redirect_within_whitelist(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #24
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "danbooru.donmai.us":
            return httpx.Response(302, headers={"location": "https://cdn.donmai.us/real.png"})
        return httpx.Response(200, content=b"IMG")

    calls = _install_transport(monkeypatch, handler)
    assert scraper.download("https://danbooru.donmai.us/a.png") == b"IMG"
    assert calls == [
        "https://danbooru.donmai.us/a.png",
        "https://cdn.donmai.us/real.png",
    ]


def test_download_rejects_redirect_to_disallowed_target(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #24: every redirect hop is re-validated before being fetched
    calls = _install_transport(
        monkeypatch,
        lambda _req: httpx.Response(302, headers={"location": "http://192.168.1.1/admin"}),
    )
    with pytest.raises(ScraperError):
        scraper.download("https://cdn.donmai.us/a.png")
    assert calls == ["https://cdn.donmai.us/a.png"], "redirect target must not be fetched"


def test_download_gives_up_after_max_redirects(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #24
    calls = _install_transport(
        monkeypatch,
        lambda _req: httpx.Response(302, headers={"location": "https://cdn.donmai.us/loop.png"}),
    )
    with pytest.raises(ScraperError):
        scraper.download("https://cdn.donmai.us/start.png")
    assert len(calls) == base_mod.MAX_REDIRECTS + 1


def test_download_redirect_without_location_fails_closed(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #24 hardening: on httpx>=0.28 ``is_redirect`` is True for any 3xx,
    # even without a Location header — a malformed redirect must surface as a
    # clean ScraperError (via raise_for_status), not a KeyError, and must not
    # be treated as a followable hop.
    calls = _install_transport(monkeypatch, lambda _req: httpx.Response(302))
    with pytest.raises(ScraperError):
        scraper.download("https://cdn.donmai.us/a.png")
    assert calls == ["https://cdn.donmai.us/a.png"]


def test_allowed_hosts_wildcard_semantics(scraper: DanbooruScraper) -> None:
    # audit #24: "*.donmai.us" matches the bare domain + subdomains, nothing else
    assert scraper._host_allowed("cdn.donmai.us")
    assert scraper._host_allowed("danbooru.donmai.us")
    assert scraper._host_allowed("donmai.us")
    assert not scraper._host_allowed("evil-donmai.us")
    assert not scraper._host_allowed("donmai.us.evil.com")
    assert not scraper._host_allowed("")


def test_base_scraper_default_whitelist_is_empty() -> None:
    # audit #24: a scraper that declares no hosts downloads nothing
    class Bare(base_mod.Scraper):
        source_site = "bare"

        def search(self, query: str, *, page: int = 1, limit: int = 100):
            return []

        def fetch(self, source_id: str):
            raise NotImplementedError

    with pytest.raises(ScraperError):
        Bare().download("https://anything.example.com/a.png")


# --- download size cap (audit #25) ----------------------------------------------

def test_download_over_size_cap_raises(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #25
    monkeypatch.setattr(base_mod, "MAX_DOWNLOAD_BYTES", 16)
    _install_transport(monkeypatch, lambda _req: httpx.Response(200, content=b"x" * 64))
    with pytest.raises(ScraperError):
        scraper.download("https://cdn.donmai.us/huge.png")


def test_download_within_cap_returns_bytes(monkeypatch, scraper: DanbooruScraper) -> None:
    # audit #25
    _install_transport(monkeypatch, lambda _req: httpx.Response(200, content=b"HELLO"))
    assert scraper.download("https://cdn.donmai.us/ok.png") == b"HELLO"


# --- retry logging (audit #39) ---------------------------------------------------

def test_danbooru_retry_logs_warning(monkeypatch, caplog) -> None:
    # audit #39: a 429/5xx retry surfaces as a WARNING log
    monkeypatch.setattr(danbooru_mod, "rate_limit_sleep", lambda _s: None)
    seen = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        if seen["n"] == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, content=b"[]", headers={"content-type": "application/json"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    s = DanbooruScraper(rate_limit_s=0, max_retries=2, client=http_client)
    with caplog.at_level(logging.WARNING, logger="app.scrapers.danbooru"):
        s.search("query")

    warnings = [
        r for r in caplog.records
        if r.name == "app.scrapers.danbooru" and r.levelno == logging.WARNING
    ]
    assert warnings, "a retried 429 must emit a WARNING"
    assert "attempt=1" in warnings[0].getMessage()


# --- upstream file_ext convergence (audit #6, adapter side) ----------------------

def test_danbooru_parse_post_converges_file_ext(scraper: DanbooruScraper) -> None:
    # audit #6: traversal-shaped ext collapses to the "png" fallback…
    sp = scraper._parse_post({
        "id": 1,
        "file_url": "https://cdn.donmai.us/1.bin",
        "file_ext": "png/../../../evil",
    })
    assert sp.file_ext == "png"

    # …and casing is normalized like a well-formed value.
    sp = scraper._parse_post({
        "id": 2,
        "file_url": "https://cdn.donmai.us/2.jpg",
        "file_ext": "JPG",
    })
    assert sp.file_ext == "jpg"


# --- packaging + config regressions (audit #15 / #41) ----------------------------

def test_httpx_is_a_runtime_dependency() -> None:
    # audit #15: scrapers import httpx at module top level, so it must be a
    # main dependency, not a dev extra
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert any(dep.strip().startswith("httpx") for dep in data["project"]["dependencies"])


def test_settings_has_no_dead_secret_key() -> None:
    # audit #41: secret_key had zero consumers; sessions use random DB tokens
    assert "secret_key" not in Settings.model_fields
