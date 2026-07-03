# Danbooru 抓取器 — 执行计划

> 配套 `prd.md` + `design.md`。按序执行，每步带校验门。

## 0. 前置（task.py start 前已完成）
- [x] prd.md（7 条 AC，无开放问题）
- [x] design.md（7 节：边界/数据结构/编排/mock 策略/决策/回滚/风险）
- [x] implement.md（本文件）

## 1. scrapers/base.py — 抽象 + dataclass

- [ ] **1.1** 新建 `backend/app/scrapers/__init__.py` + `base.py`：`ScrapedTag`、`ScrapedPost` dataclass + `Scraper` 抽象基类（search/fetch/download，source_site 属性）。
- [ ] **1.2** 在 `services/errors.py` 加 `ScraperError(AppError)`（503 或 502，code `scraper_error`）。
  - **校验门**：`python -c "from app.scrapers.base import Scraper, ScrapedPost, ScrapedTag"`。

## 2. scrapers/danbooru.py — 适配器

- [ ] **2.1** `DanbooruScraper`：`__init__(rate_limit_s=1.0, max_retries=3)`、`_get(path, params)`（httpx + time.sleep 限速 + 指数退避重试）。
- [ ] **2.2** `search(query, page, limit)`：GET /posts.json，解析 JSON → list[ScrapedPost]（字段映射：id/file_url/file_ext/rating/tag_string* → ScrapedPost）。
- [ ] **2.3** `fetch(source_id)`：GET /posts/{id}.json → 单 ScrapedPost。
- [ ] **2.4** `fetch_implications()`：GET /tag_implications.json 分页 → [(ant_name, con_name)]。
- [ ] **2.5** `download(image_url)`：httpx GET 字节。
  - **校验门**：`python -c "from app.scrapers.danbooru import DanbooruScraper; s=DanbooruScraper(); print(s.source_site, s.search, s.fetch)"`。

## 3. services/scrape.py — 编排

- [ ] **3.1** `ScrapeResult` dataclass（new/duplicate/failed）。
- [ ] **3.2** `scrape_to_db(db, scraper, query, limit=20)`：search → source 去重 → download → ingest（DuplicateError 走 duplicate）→ tag_post → 计数 + 错误隔离（design §3.1）。
- [ ] **3.3** `bootstrap_implications(db, scraper)`：fetch_implications → get_or_create tags → create_implication（ConflictError 跳过）→ 计数。
  - **校验门**：`python -c "from app.services.scrape import scrape_to_db, bootstrap_implications, ScrapeResult"`。

## 4. tests/test_scrape.py — 全 mock

- [ ] **4.1** `FakeScraper(Scraper)`：硬编码 ScrapedPost 列表（含已存在 source、md5 重复、正常、失败各一个）+ 假字节下载 + 假 implications。
- [ ] **4.2** `test_scrape_to_db_source_dedup`（AC3）：已存在 source 跳过下载。
- [ ] **4.3** `test_scrape_to_db_md5_dedup`（AC3）：download 后 md5 命中 DuplicateError → duplicate 计数。
- [ ] **4.4** `test_scrape_to_db_ingest_and_tag`（AC4）：正常 post 入库 + tag_post 物化（查 post_tags）。
- [ ] **4.5** `test_scrape_to_db_error_isolation`（AC6）：单张失败不中断，failed 计数。
- [ ] **4.6** `test_bootstrap_implications`（AC5）：implication 入库 + 环被 409 跳过。
- [ ] **4.7** `test_danbooru_parser`（AC2）：mock httpx 响应伪造 Danbooru JSON → 断言 ScrapedPost 字段映射正确 + 重试被触发（伪造 429 后重试成功）。
  - **校验门**：`cd backend && python -m pytest tests/test_scrape.py -v` 全绿。

## 5. 全量回归 + spec 自查

- [ ] **5.1** `cd backend && python -m pytest -v` → 原 39 + 新 scrape 测试全绿。
- [ ] **5.2** spec 自查：grep 确认 media.py/tags.py 未被改（只调）、scrapers/ + services/scrape.py 不导入 fastapi、零 schema 变更、无真实网络请求（测试无 `httpx.get` 直调真实 URL）。

## 校验命令汇总

```bash
cd backend
python -m pytest -v                              # 全量（5.1）
python -m pytest tests/test_scrape.py -v         # 仅 scrape（4.7 后）
python -c "from app.scrapers.danbooru import DanbooruScraper"   # 2.5
```

## 回滚点

- **步骤 1-2 后**：删 `scrapers/`，DB 无影响。
- **步骤 3 后**：删 `services/scrape.py`，DB 无影响。
- **全切片回滚**：`git revert`，零 schema 变更，无迁移需反向。

## 风险点（来自 design §7）

- Danbooru API 字段映射可能过时（mock 用文档快照，真实跑可能要调）。
- Cloudflare 403 持续（真实抓取需用户配代理，不在 AC）。
