# Danbooru 抓取器 — 技术设计

> 配套 `prd.md`。本切片交付 scraper 抽象 + Danbooru 适配器 + 抓取→入库编排服务。复用切片 3 `media.ingest` + 切片 2 剩余 `tag_post` / `create_implication`。真实抓取受 Cloudflare 403 阻断，测试全 mock。

## 1. 模块边界

```
backend/app/scrapers/__init__.py        ← 新增：包导出
backend/app/scrapers/base.py            ← 新增：Scraper 抽象基类 + ScrapedPost dataclass
backend/app/scrapers/danbooru.py        ← 新增：Danbooru 适配器（search/fetch/download/implications）
backend/app/services/scrape.py          ← 新增：编排服务（scrape_to_db + bootstrap_implications）
backend/tests/test_scrape.py            ← 新增：全 mock 测试
```

**不碰**：`services/media.py`、`services/tags.py`（只调不改）、`api/`（本切片无端点）、`models/`、`alembic/`、`config.py`（baseurl 可硬编码或后续加 config）。

层级守约：`scrapers/` + `services/scrape.py` 都不导入 fastapi；纯服务，被切片 8 的 import API 调。`scrapers/` 只管「取元数据 + 下载字节」，`services/scrape.py` 是跨层胶水（调 scraper + media.ingest + tag_post + create_implication）。

## 2. 数据结构

### 2.1 `scrapers/base.py` — 抽象 + dataclass

```python
from __future__ import annotations
from dataclasses import dataclass, field
import abc

@dataclass
class ScrapedTag:
    name: str
    category: str  # general/character/copyright/artist/meta

@dataclass
class ScrapedPost:
    source_id: str          # Danbooru post id (str for uniformity)
    image_url: str          # direct file URL to download
    tags: list[ScrapedTag]
    rating: str             # safe/questionable/explicit (map from Danbooru s/q/e)
    source_url: str         # the post's page URL
    file_ext: str           # png/jpg/gif/webp
    is_animated: bool       # gif/webp animated (Danbooru tags: animated)

class Scraper(abc.ABC):
    """Site-agnostic scraper interface. Implementations handle API specifics,
    rate limiting, and retries."""
    source_site: str  # 'danbooru' | 'gelbooru' | ...

    @abc.abstractmethod
    def search(self, query: str, page: int = 1, limit: int = 100) -> list[ScrapedPost]: ...

    @abc.abstractmethod
    def fetch(self, source_id: str) -> ScrapedPost: ...

    def download(self, image_url: str) -> bytes:
        """Download image bytes. Concrete default in base using httpx, override-able."""
        ...
```

### 2.2 `scrapers/danbooru.py` — 适配器

```python
class DanbooruScraper(Scraper):
    source_site = "danbooru"
    BASE_URL = "https://danbooru.donmai.us"
    # Danbooru rating map: 's'→safe, 'q'→questionable, 'e'→explicit, 'g'→safe
    _RATING_MAP = {"s": "safe", "q": "questionable", "e": "explicit", "g": "safe"}

    def __init__(self, *, rate_limit_s: float = 1.0, max_retries: int = 3): ...

    def search(self, query, page=1, limit=100) -> list[ScrapedPost]:
        # GET /posts.json?tags=<query>&page=<page>&limit=<limit>
        # parse each post: id, file_url, file_ext, rating, tag_string → split
        # rate-limit + retry wrapper
        ...

    def fetch(self, source_id) -> ScrapedPost:
        # GET /posts/{id}.json → single post
        ...

    def fetch_implications(self) -> list[tuple[str, str]]:
        # GET /tag_implications.json?search[status]=active (paginated)
        # → [(antecedent_name, consequent_name), ...]
        ...

    def _get(self, path, params) -> list | dict:
        # httpx GET with: time.sleep(rate_limit_s) before each call,
        # exponential backoff retry on 429/5xx/network error (max_retries)
        ...
```

**Danbooru 字段映射**（按其公共 API JSON）：
- `id` → `source_id`（str 化）
- `file_url`（或 `large_file_url`/`preview_file_url` 降级）→ `image_url`
- `file_ext` → `file_ext`
- `rating`（s/q/e/g）→ 映射成 safe/questionable/explicit
- `tag_string`（空格分隔）→ `tags`，类别从 `tag_string_general/character/copyright/artist/meta` 拆分
- `is_animated`：检查 `tag_string` 含 "animated" 或 file_ext=gif
- `source_url`：`{BASE_URL}/posts/{id}`

**限速**：每次 `_get` 前 `time.sleep(rate_limit_s)`。单线程单用户，令牌桶无意义。

**重试**：429/5xx/网络错误 → 指数退避 `2 ** attempt` 秒，最多 `max_retries` 次，仍失败抛 `ScraperError`（新 AppError 子类，或复用 AppError）。

## 3. 编排服务（`services/scrape.py`）

### 3.1 `scrape_to_db` — 抓取→入库编排

```
scrape_to_db(db, scraper: Scraper, query: str, limit: int = 20) -> ScrapeResult
  │
  ├─ 1. results = scraper.search(query, limit=limit)
  ├─ 2. 对每个 ScrapedPost sp：
  │      ├─ (a) source 去重：查 Post(source_site=scraper.source_site, source_id=sp.source_id)
  │      │      命中 → duplicate += 1；continue（不下载）
  │      ├─ (b) 下载：data = scraper.download(sp.image_url)
  │      ├─ (c) try: post = media.ingest(db, data, source_site=scraper.source_site,
  │      │              source_id=sp.source_id, source_url=sp.source_url,
  │      │              file_ext=sp.file_ext, is_animated=sp.is_animated,
  │      │              rating=sp.rating)
  │      │    except DuplicateError: duplicate += 1；continue（md5 命中，design §4 两阶段）
  │      │    except Exception: failed += 1；continue（错误隔离，不中断）
  │      ├─ (d) tags.tag_post(db, post.id, [t.name for t in sp.tags])
  │      └─ new += 1
  └─ 3. return ScrapeResult(new, duplicate, failed)
```

**两阶段去重**（design §4 Scrape Dedup）：(a) 列表阶段查 source 跳过已抓（不下载，省带宽）；(b) 下载后 md5 命中走 DuplicateError（同图不同源/改 id）。两者都验证。

**错误隔离**：单张下载/解析失败记 `failed` 继续，不中断整批。

### 3.2 `bootstrap_implications` — implication 建库

```
bootstrap_implications(db, scraper) -> int
  │
  ├─ 1. pairs = scraper.fetch_implications()  # [(ant_name, con_name), ...]
  ├─ 2. 对每对 (ant_name, con_name)：
  │      ├─ get_or_create Tag(ant_name) / Tag(con_name) 拿 id
  │      ├─ try: tags.create_implication(db, ant_id, con_id)
  │      │    except ConflictError: skip（环或重复，不中断）
  │      └─ 计数成功数
  └─ 3. return 成功数
```

复用 `create_implication` 的防环 + 回填（切片 2 剩余）。环被 409 跳过不中断整体。

### 3.3 `ScrapeResult`

```python
@dataclass
class ScrapeResult:
    new: int = 0
    duplicate: int = 0
    failed: int = 0
```

## 4. mock 测试策略（`tests/test_scrape.py`）

**核心：不发真实网络请求**。用一个 `FakeScraper(Scraper)` 直接返回硬编码 `ScrapedPost` 列表 + 假字节，绕过 httpx。

- `FakeScraper.search` 返回 3 个 ScrapedPost（含 1 个已存在 source_id 测去重、1 个 md5 重复测 DuplicateError、1 个正常）。
- `FakeScraper.download` 返回 `_png_bytes()`（复用 test_media 的造图）。
- `FakeScraper.fetch_implications` 返回 [("a","b"), ("b","a")] 测防环（第二对成环 409 跳过）。

测试用 `client` fixture（tmp DB）+ `media_dir` fixture（tmp 媒体目录），调 `scrape_to_db(db, FakeScraper(), "test")`，断言：
- AC3：已存在 source 跳过下载（FakeScraper.download 调用次数 = 非去重数）。
- AC4：正常 post 入库 + tag_post 物化（查 post_tags）。
- AC6：failed 计数 + 不中断。
- AC5：bootstrap_implications 后 DB 有 TagImplication 行 + 环被跳过。

**danbooru.py 自身的 search/fetch 解析**测试：mock httpx 响应（`httpx.MockTransport` 或 monkeypatch `httpx.get`），伪造 Danbooru JSON，断言解析出的 ScrapedPost 字段正确 + 限速/重试被调用。这块验证适配器「按 API 文档解析对不对」，不验证真实可达。

## 5. 决策记录

| # | 决策 | 依据 |
|---|---|---|
| D1 | Cloudflare 403 → **全 mock 测试** | 用户拍板。真实抓取不可行（JS challenge 非 UA 能绕）；切片价值在抽象+编排逻辑，mock 能验证正确性。真实可达是运维问题（用户配 HTTPS_PROXY httpx 自动认）。 |
| D2 | 编排放 `services/scrape.py` | 跨层胶水（scraper + media.ingest + tag_post），不属于单个 scraper 适配器。scraper 只管取元数据+字节，编排管入库。 |
| D3 | implication bootstrap 本切片做 | design §4 明确「建库拉一次」。复用 create_implication 防环+回填。同样 mock 测试。 |
| D4 | 限速 `time.sleep` 非令牌桶 | 单线程单用户，令牌桶过度工程。sleep 1s 够礼貌。 |
| D5 | 重试指数退避，max 3 次 | 429/5xx/网络错误，`2**attempt` 秒。仍失败抛 ScraperError。 |
| D6 | 不接 API 端点 | POST /api/import/scrape 属切片 8 导入页。本切片只做服务，端点留切片 8。 |
| D7 | 新增 `ScraperError(AppError)` | 适配器最终失败需要一个错误类型（重试耗尽）。复用 AppError 体系。 |

## 6. 兼容性 / 回滚

- **零 schema 变更**，无迁移风险。
- 新增 `scrapers/` 包 + `services/scrape.py`：回滚删文件即可，DB 无影响。
- `media.py`/`tags.py` 只调不改，向后兼容。
- 真实抓取可达性不在 AC：用户配代理后代码不改即能跑。

## 7. 风险

- **Danbooru API 字段映射可能过时**：Danbooru 改过字段名（如 `file_url` → `file_url`/`large_file_url`）。mock 测试用文档快照，真实跑可能要调字段。AC 标注「按当前 API 文档，真实字段以实际为准」。
- **Cloudflare 403 持续**：本切片交付后真实抓取仍不可行，需用户配代理。这是已知约束，诚实标注在 AC。
- **implication 全集可能很大**：Danbooru implication 上万条，bootstrap 全量拉可能慢。但单用户建库一次，可接受；mock 测试只测少量样本。
