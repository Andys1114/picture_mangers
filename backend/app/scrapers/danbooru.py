"""Danbooru scraper adapter (first concrete ``Scraper`` implementation).

Talks to the Danbooru public API at https://danbooru.donmai.us anonymously.
Polite-crawl: 1 req/s rate limit + exponential backoff retries on transient
failures (429 / 5xx / network errors).

⚠️ Known constraint: the Danbooru public API is fronted by Cloudflare, which
returns a 403 JS-challenge page to non-browser clients. Real scraping from a
typical dev machine is blocked; tests therefore mock httpx entirely. The code
is correct per the current API docs; reaching the site for real requires a
proxy (HTTPS_PROXY, which httpx honors automatically) or an environment
Cloudflare doesn't challenge.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.scrapers.base import Scraper, ScrapedPost, ScrapedTag, rate_limit_sleep
from app.services.errors import ScraperError

# Danbooru rating letters → project rating buckets.
# 'g' (general) is an older Danbooru rating folded into 'safe' here.
_RATING_MAP = {"s": "safe", "q": "questionable", "e": "explicit", "g": "safe"}

# Danbooru tag-string fields → project categories. Each field is a
# space-separated list of tag names in that category.
_TAG_CATEGORY_FIELDS = {
    "tag_string_general": "general",
    "tag_string_character": "character",
    "tag_string_copyright": "copyright",
    "tag_string_artist": "artist",
    "tag_string_meta": "meta",
}


class DanbooruScraper(Scraper):
    """Scraper for https://danbooru.donmai.us (anonymous public API)."""

    source_site = "danbooru"
    BASE_URL = "https://danbooru.donmai.us"

    def __init__(
        self,
        *,
        rate_limit_s: float = 1.0,
        max_retries: int = 3,
        client: httpx.Client | None = None,
    ) -> None:
        self._rate_limit_s = rate_limit_s
        self._max_retries = max_retries
        # Caller may inject a client (e.g. with a MockTransport) for tests.
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=True)

    # --- HTTP core (rate-limited + retried) --------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET ``BASE_URL/path`` with rate-limiting + exponential backoff.

        Retries on 429 / 5xx / network errors up to ``max_retries`` times,
        sleeping ``2**attempt`` seconds between attempts. Raises ScraperError
        if all retries are exhausted.
        """
        url = f"{self.BASE_URL}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            rate_limit_sleep(self._rate_limit_s)
            try:
                resp = self._client.get(url, params=params)
                if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                    raise httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}", request=resp.request, response=resp
                    )
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                # ValueError covers malformed-JSON responses.
                last_exc = exc
                if attempt < self._max_retries:
                    backoff = 2 ** attempt
                    rate_limit_sleep(float(backoff))
                    continue
        raise ScraperError(f"Danbooru 请求失败（重试耗尽）: {path}") from last_exc

    # --- Scraper interface --------------------------------------------------

    def search(self, query: str, *, page: int = 1, limit: int = 100) -> list[ScrapedPost]:
        """Search posts by tag query (space-separated tags, AND)."""
        raw = self._get("/posts.json", {"tags": query, "page": page, "limit": limit})
        if not isinstance(raw, list):
            raise ScraperError("Danbooru search 返回非列表")
        return [self._parse_post(p) for p in raw]

    def fetch(self, source_id: str) -> ScrapedPost:
        """Fetch a single post by its Danbooru id."""
        raw = self._get(f"/posts/{source_id}.json")
        if not isinstance(raw, dict):
            raise ScraperError("Danbooru fetch 返回非对象")
        return self._parse_post(raw)

    def fetch_implications(self) -> list[tuple[str, str]]:
        """Pull active tag implications (antecedent→consequent name pairs).

        Paginates through /tag_implications.json. Used by the bootstrap step
        to populate the local implication graph (each pair is handed to
        ``tags.create_implication``, which dedupes + cycle-checks).
        """
        pairs: list[tuple[str, str]] = []
        page = 1
        while True:
            raw = self._get(
                "/tag_implications.json",
                {"search[status]": "active", "limit": 200, "page": page},
            )
            if not isinstance(raw, list) or not raw:
                break
            for row in raw:
                ant = row.get("antecedent_name")
                con = row.get("consequent_name")
                if ant and con:
                    pairs.append((ant, con))
            if len(raw) < 200:
                break
            page += 1
        return pairs

    # --- parsing ------------------------------------------------------------

    def _parse_post(self, p: dict[str, Any]) -> ScrapedPost:
        """Map a Danbooru post JSON object onto a ScrapedPost."""
        post_id = str(p["id"])
        # file_url is the original; fall back to large/preview if deleted/missing.
        image_url = p.get("file_url") or p.get("large_file_url") or p.get("preview_file_url", "")
        file_ext = p.get("file_ext", "png") or "png"
        rating = _RATING_MAP.get(p.get("rating", "s"), "safe")
        source_url = f"{self.BASE_URL}/posts/{post_id}"

        tags: list[ScrapedTag] = []
        for field, category in _TAG_CATEGORY_FIELDS.items():
            for name in (p.get(field) or "").split():
                if name:
                    tags.append(ScrapedTag(name=name, category=category))

        # Animated: Danbooru tags 'animated' / 'animated_gif', or ext is gif.
        tag_names = {t.name for t in tags}
        is_animated = "animated" in tag_names or file_ext == "gif"

        return ScrapedPost(
            source_id=post_id,
            image_url=image_url,
            tags=tags,
            rating=rating,
            source_url=source_url,
            file_ext=file_ext,
            is_animated=is_animated,
        )
