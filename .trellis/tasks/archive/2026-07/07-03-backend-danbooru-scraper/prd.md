# Danbooru 抓取器 (scraper 抽象 + danbooru 适配器) — PRD

> 父任务：`06-28-gallery-app`（design.md §4 抓取路径 B + §6 import 端点）。父切片拆分中的 **切片 4**，后端「数据进入」的最后一块拼图。复用切片 3（`media.ingest`）+ 切片 2 剩余（`tag_post` / `create_implication`），三者合起来形成「抓取 → 下载 → 入库 → 物化标签」端到端。

## 1. Goal / 用户价值

把后端「摄入内核 + 标签写入侧」接到真实数据源：交付 scraper 抽象（`scrapers/base.py`）+ Danbooru 首个适配器（`scrapers/danbooru.py`）+ 抓取→入库编排服务（`services/scrape.py`），让 `POST /api/import/scrape`（切片 8 接端点）能调它抓图入库带标签。交付后，配合切片 8 导入页 UI，用户输查询 → 抓取 → 图自动入库带标签 + implication 物化。

## 2. 已确认事实（来自 codebase/spec/网络探测）

- **父 design.md §4 抓取路径 B**：`scrapers/base.py` 抽象基类（`search(query, page) → list[ScrapedPost]`、`fetch(post_id) → ScrapedPost`）；`ScrapedPost` dataclass（source_id、image_url、tags[{name, category}]、rating、source_url、implications[]）；`scrapers/danbooru.py`（baseurl `https://danbooru.donmai.us`，匿名公共 API，限速 1 req/s，指数退避重试）；implication 从 Danbooru tags 端点批量拉取（建库拉一次 + 增量）。
- **父 design.md §6 import 端点**：`POST /api/import/scrape {query, source, limit}` → `{task_id}`；`GET /api/tasks/{id}` 进度。**属切片 8，本切片只做 scraper + 编排服务，不接端点**。
- **复用已就位**：
  - 切片 3 `services/media.py:ingest(db, data, *, source_*, file_ext, is_animated, rating)` —— 下载字节喂它入库（含 md5 去重抛 DuplicateError + source 部分唯一索引）。
  - 切片 2 剩余 `services/tags.py:tag_post(db, post_id, names)` —— 抓回标签喂它物化（算闭包 + post_count）。
  - 切片 2 剩余 `services/tags.py:create_implication(db, ant, con)` —— implication 关系喂它建 + 回填。
- **去重已就位**：`media.ingest` 的 md5 精确去重 + `(source_site, source_id)` 部分唯一索引（design §4「Scrape Dedup」两阶段：列表阶段查 source 跳过已抓、下载后 md5 走 duplicate 流）。
- **环境**：httpx 0.28.1 已装；Pillow/imagehash 已装。
- **⚠️ 关键约束：Danbooru 公共 API 被 Cloudflare 403 拦截**。本机直连 `https://danbooru.donmai.us/posts.json` 返回 403 + "Just a moment..." JS challenge 页。Cloudflare 的 JS challenge 不是简单 UA/referer 能绕的。**真实抓取在本机不可行，测试全 mock**。

## 3. 范围

### In scope
- **`scrapers/base.py`** —— 抽象基类 `Scraper`（`search(query, page) -> list[ScrapedPost]`、`fetch(post_id) -> ScrapedPost`）+ `ScrapedPost` dataclass（source_id、image_url、tags、rating、source_url）。
- **`scrapers/danbooru.py`** —— Danbooru 适配器：baseurl、匿名公共 API、`time.sleep(1)` 限速（单线程单用户够，令牌桶过度工程）、指数退避重试、search/fetch 实现 + `_download(image_url) -> bytes`。
- **`scrapers/danbooru_implications.py`**（或并入 danbooru.py）—— `fetch_implications() -> list[tuple[str, str]]`：从 Danbooru tags 端点批量拉 antecedent→consequent 关系。
- **`services/scrape.py`** —— 编排服务（跨层胶水）：
  - `scrape_to_db(db, scraper, query, limit) -> ScrapeResult`：循环 search → 查 source 去重 → 下载字节 → `media.ingest` → `tag_post` → 返回（新增/重复/失败计数）。
  - `bootstrap_implications(db, scraper)`：拉 Danbooru implication 全集 → 对每对调 `create_implication`（复用切片 2 剩余的防环 + 回填）。
- **`tests/test_scrape.py`** —— 全 mock：httpx 响应伪造 + fixture ScrapedPost，验证编排逻辑（去重、ingest 调用、tag_post 调用、计数）。

### Out of scope
- 后台任务调度 / APScheduler / `/api/tasks/{id}` 进度端点（切片 8）。
- `POST /api/import/scrape` 端点（切片 8 导入页）。
- 本地导入（路径 A，切片 8）。
- gelbooru/moebooru 适配器（父 design 预留，本切片只做 danbooru）。
- 真实 Danbooru 端到端测试（Cloudflare 403，不可行）。
- phash 查邻标记 duplicate（留切片 8 异步调度）。
- 代理/Cloudflare 绕过配置（运维问题，不在代码 AC 内；用户配 HTTPS_PROXY 后 httpx 自动认）。

## 4. 验收标准

- [ ] **AC1 — scraper 抽象 + ScrapedPost**：`scrapers/base.py` 定义 `Scraper` 基类（search/fetch 抽象方法）+ `ScrapedPost` dataclass（source_id/image_url/tags/rating/source_url 字段）。
- [ ] **AC2 — danbooru 适配器**：`scrapers/danbooru.py` 实现 search/fetch，按 Danbooru 公共 API 文档构造 URL + 解析 JSON；限速（`time.sleep(1)`）+ 指数退避重试（mock 触发失败验证重试次数）。
- [ ] **AC3 — 编排服务去重**：`scrape_to_db` 对已存在的 `(source_site, source_id)` 跳过下载（列表阶段 source 去重）；下载后 md5 命中走 DuplicateError（不重复入库）—— 两阶段去重各自验证。
- [ ] **AC4 — 编排服务入库 + 物化**：mock ScrapedPost → `scrape_to_db` 调 `media.ingest`（source_site='danbooru' + source_id + rating）+ `tag_post`（标签名列表）→ Post 入库带正确标签。
- [ ] **AC5 — implication bootstrap**：`bootstrap_implications` mock 拉回 [(A,B),...] → 对每对调 `create_implication` → DB 有对应 TagImplication 行（复用防环，环被 409 跳过不中断整体）。
- [ ] **AC6 — 计数与错误隔离**：`scrape_to_db` 返回 `{new, duplicate, failed}` 计数；单张下载/解析失败不中断整批（记录 failed 继续）。
- [ ] **AC7 — 回归**：`pytest -v` 全绿（原 39 + 新增 scrape 测试）；spec 自查（不重写 ingest/tag_post 逻辑、scraper 层不导入 fastapi、零 schema 变更）。

## 5. 约束

- 零 schema 变更（source_* 字段、部分唯一索引都齐）。
- 复用 `media.ingest` + `tag_post` + `create_implication`，不重写摄入/物化逻辑。
- 限速 1 req/s（`time.sleep`）+ 指数退避重试。
- **测试全 mock，不发真实网络请求**（Cloudflare 403 + 网络不稳定）。
- `from __future__ import annotations` + 类型注解 + scraper 层不导入 fastapi（纯服务）。
- 真实抓取可达性不在 AC 内（用户配代理后 httpx 自动认 HTTPS_PROXY）。

## 6. 开放问题

无（4 个边界问题已与用户敲定：Cloudflare 403 → 全 mock 测试；编排放 services/scrape.py；implication bootstrap 本切片做也 mock；限速用 time.sleep 非令牌桶）。
