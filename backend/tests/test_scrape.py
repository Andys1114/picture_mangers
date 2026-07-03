"""Scraper + scrape-to-db orchestration tests (slice 4).

Fully mocked — no real network requests. A ``FakeScraper`` returns hardcoded
``ScrapedPost`` objects + fake image bytes so the orchestration logic (dedup,
ingest, tag materialization, error isolation, implication bootstrap) is tested
without touching Danbooru. The Danbooru adapter's JSON parsing is tested
separately with ``httpx.MockTransport``.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image
from sqlalchemy import select
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.models.tag import Tag, TagImplication
from app.scrapers.base import Scraper, ScrapedPost, ScrapedTag
from app.scrapers import danbooru as danbooru_mod
from app.scrapers.danbooru import DanbooruScraper
from app.services import media, scrape, tags
from app.services.errors import ScraperError


# --- fixtures --------------------------------------------------------------

@pytest.fixture()
def media_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "media"
    d.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "media_dir", str(d))
    # Zero out rate-limit sleeps so tests don't actually wait.
    monkeypatch.setattr(danbooru_mod, "rate_limit_sleep", lambda _s: None)
    return settings.media_path


@pytest.fixture()
def db():
    s = db_module.SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _png_bytes(w: int, h: int, rgb: tuple[int, int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(buf, format="PNG")
    return buf.getvalue()


class FakeScraper(Scraper):
    """In-memory scraper returning canned posts + bytes. ``source_site`` is
    'fake' so it never collides with real source dedup assumptions."""

    source_site = "danbooru"

    def __init__(self, posts: list[ScrapedPost], byte_map: dict[str, bytes], implications=None):
        self._posts = posts
        self._byte_map = byte_map
        self._implications = implications or []
        self.download_calls: list[str] = []

    def search(self, query: str, *, page: int = 1, limit: int = 100) -> list[ScrapedPost]:
        return self._posts[:limit]

    def fetch(self, source_id: str) -> ScrapedPost:
        return next(p for p in self._posts if p.source_id == source_id)

    def download(self, image_url: str) -> bytes:
        self.download_calls.append(image_url)
        if image_url not in self._byte_map:
            raise ScraperError(f"no bytes for {image_url}")
        return self._byte_map[image_url]

    def fetch_implications(self) -> list[tuple[str, str]]:
        return list(self._implications)


def _scraped(source_id: str, rgb_name: str, rating: str = "safe", animated: bool = False) -> ScrapedPost:
    return ScrapedPost(
        source_id=source_id,
        image_url=f"https://fake/{source_id}.png",
        tags=[ScrapedTag(name=rgb_name, category="general")],
        rating=rating,
        source_url=f"https://fake/posts/{source_id}",
        file_ext="png",
        is_animated=animated,
    )


# --- AC3: source dedup (list stage) ----------------------------------------

def test_scrape_source_dedup_skips_download(client: TestClient, media_dir: Path, db) -> None:
    """AC3: a scraped post whose (source_site, source_id) already exists is
    skipped BEFORE download — download() is not called for it."""
    # Pre-ingest a post so its source_id is already present.
    pre = _scraped("100", "red")
    media.ingest(
        db, _png_bytes(10, 10, (255, 0, 0)),
        source_site="danbooru", source_id="100", source_url=pre.source_url,
        file_ext="png", is_animated=False, rating="safe",
    )

    scraper = FakeScraper(
        posts=[pre, _scraped("200", "blue")],
        byte_map={"https://fake/200.png": _png_bytes(20, 20, (0, 0, 255))},
    )
    r = scrape.scrape_to_db(db, scraper, "any")
    assert "https://fake/100.png" not in scraper.download_calls, "existing source must skip download"
    assert r.duplicate == 1
    assert r.new == 1


# --- AC3: md5 dedup (ingest stage) -----------------------------------------

def test_scrape_md5_dedup_counts_as_duplicate(client: TestClient, media_dir: Path, db) -> None:
    """AC3: two scraped posts with the SAME image bytes (same md5) — the second
    hits DuplicateError at ingest and is counted duplicate, not failed."""
    same_bytes = _png_bytes(30, 30, (1, 2, 3))
    scraper = FakeScraper(
        posts=[_scraped("301", "x"), _scraped("302", "x")],  # different source_id, same bytes
        byte_map={"https://fake/301.png": same_bytes, "https://fake/302.png": same_bytes},
    )
    r = scrape.scrape_to_db(db, scraper, "any")
    assert r.new == 1
    assert r.duplicate == 1
    assert r.failed == 0


# --- AC4: ingest + tag materialization -------------------------------------

def test_scrape_ingest_and_tag(client: TestClient, media_dir: Path, db) -> None:
    """AC4: a normal scraped post is ingested with source_* fields and its tags
    materialized (post_tags has the tag)."""
    from app.models.post import Post
    from app.models.tag import PostTag

    sp = ScrapedPost(
        source_id="400",
        image_url="https://fake/400.png",
        tags=[ScrapedTag(name="hatsune_miku", category="character"),
              ScrapedTag(name="vocaloid", category="copyright")],
        rating="safe",
        source_url="https://fake/posts/400",
        file_ext="png",
        is_animated=False,
    )
    scraper = FakeScraper(posts=[sp], byte_map={sp.image_url: _png_bytes(40, 40, (0, 255, 0))})
    r = scrape.scrape_to_db(db, scraper, "miku")
    assert r.new == 1 and r.failed == 0

    post = db.execute(select(Post).where(Post.source_id == "400")).scalar_one()
    assert post.rating == "safe"
    assert post.source_site == "danbooru"
    tagged = {db.execute(select(Tag).where(Tag.id == pt.tag_id)).scalar_one().name
              for pt in db.execute(select(PostTag).where(PostTag.post_id == post.id)).scalars().all()}
    assert "hatsune_miku" in tagged
    assert "vocaloid" in tagged


# --- AC6: error isolation --------------------------------------------------

def test_scrape_error_isolation(client: TestClient, media_dir: Path, db) -> None:
    """AC6: a download failure on one post does not abort the batch; it's
    counted as failed and processing continues."""
    scraper = FakeScraper(
        posts=[_scraped("500", "a"), _scraped("501", "b"), _scraped("502", "c")],
        byte_map={
            "https://fake/500.png": _png_bytes(1, 1, (1, 1, 1)),
            # 501 has no bytes → download raises ScraperError
            "https://fake/502.png": _png_bytes(2, 2, (2, 2, 2)),
        },
    )
    r = scrape.scrape_to_db(db, scraper, "any")
    assert r.new == 2
    assert r.failed == 1


# --- AC5: implication bootstrap --------------------------------------------

def test_bootstrap_implications(client: TestClient, media_dir: Path, db) -> None:
    """AC5: bootstrap pulls pairs and creates implications; a pair that would
    form a cycle is skipped (409) without aborting."""
    scraper = FakeScraper(
        posts=[], byte_map={},
        implications=[("parent", "child"), ("child", "parent")],  # 2nd would cycle
    )
    created = scrape.bootstrap_implications(db, scraper)
    assert created == 1, "only the non-cyclic pair is created"
    rows = db.execute(select(TagImplication)).scalars().all()
    assert len(rows) == 1
    # Both tags exist regardless (created before the implication attempt).
    assert db.execute(select(Tag).where(Tag.name == "parent")).scalar_one() is not None
    assert db.execute(select(Tag).where(Tag.name == "child")).scalar_one() is not None


# --- AC2: danbooru adapter parsing + retry (mocked httpx) -------------------

def test_danbooru_parser_and_retry(client: TestClient, media_dir: Path, db) -> None:
    """AC2: the Danbooru adapter parses posts JSON correctly and retries on a
    transient 429 before succeeding. Uses httpx.MockTransport — no real network."""
    danbooru_json = [{
        "id": 999, "file_url": "https://cdn/999.png", "file_ext": "png",
        "rating": "q", "tag_string_character": "hatsune_miku",
        "tag_string_copyright": "vocaloid", "tag_string_general": "blue_hair",
    }]
    encoded = json.dumps(danbooru_json).encode()

    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, content=encoded, headers={"content-type": "application/json"})

    transport = httpx.MockTransport(handler)
    client_http = httpx.Client(transport=transport)
    scraper = DanbooruScraper(rate_limit_s=0, max_retries=3, client=client_http)

    posts = scraper.search("hatsune_miku", limit=1)
    assert len(posts) == 1
    p = posts[0]
    assert p.source_id == "999"
    assert p.rating == "questionable"
    assert p.file_ext == "png"
    assert p.is_animated is False
    names = {t.name for t in p.tags}
    assert {"hatsune_miku", "vocaloid", "blue_hair"} == names
    assert call_count["n"] == 2, "should have retried once after the 429"


def test_danbooru_retry_exhausted_raises_scraper_error(client: TestClient, media_dir: Path, db) -> None:
    """AC2: when retries are exhausted, the adapter raises ScraperError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    transport = httpx.MockTransport(handler)
    client_http = httpx.Client(transport=transport)
    scraper = DanbooruScraper(rate_limit_s=0, max_retries=1, client=client_http)

    with pytest.raises(ScraperError):
        scraper.search("any")
