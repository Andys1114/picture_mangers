# 媒体处理管道 + 最小 Post 摄入 — PRD

> 父任务：`06-28-gallery-app`（design.md §4 导入与抓取子系统的共享媒体处理管道）。父切片拆分中的 **切片 3**，位于「切片 2 剩余（标签写入侧）」与「切片 4（Danbooru 抓取器）」之间。本切片为切片 4/8 提供可复用的摄入内核。

## 1. Goal / 用户价值

把后端从「地基有、数据进不来」推进到「给字节流就能落库」：一条自包含、可单测、可被切片 4（抓取）与切片 8（导入 API）直接复用的媒体摄入服务。md5 精确去重、Pillow 生成 thumb/preview 缩略图、imagehash 算 phash 存字段、动图保留动画。交付后 `seed_dev.py` 用真管道造数，dev 库的图就是真缩略图 + 真 phash。

## 2. 已确认事实（来自 codebase/spec 检查）

- **Post 模型已就位**（`backend/app/models/post.py`）：`md5`(unique)、`phash`(nullable str)、`is_duplicate`(bool)、`duplicate_of_id`(self-FK SET NULL)、`file_path`/`thumb_path`/`preview_path`(相对路径 str)、`file_ext`/`is_animated`/`width`/`height`/`file_size`/`rating`/`source_*` 全有。本切片**不改 schema、不加迁移**——字段都齐了，只填业务逻辑。
- **错误体系已就位**（`backend/app/services/errors.py`）：`AppError` 基类 + `Unauthorized/Conflict/NotFound` + 全局 handler 统一信封。本切片新增 `DuplicateError`。
- **`config.py`**：`media_path` 属性解析为绝对 `Path`（相对则相对 `backend/`）。`media_dir` 默认 `./media`。
- **spec 强约束**（`database-guidelines.md`「Duplicate Images」+ `quality-guidelines.md`）：
  - md5 **同步**算，命中跳过不建记录；phash **异步**算后标记 duplicate。
  - `duplicate_of_id IS NOT NULL` 是权威信号，`is_duplicate` 是快筛便利。
  - 「No `fav_count`」「搜索写时物化不读时递归」「业务逻辑不在 route」「`create_all` 禁用」「ORM/Core 参数化查询」均适用。
- **`seed_dev.py` 现状**（`backend/scripts/seed_dev.py`）：手搓 `_png_solid` 绕开 Pillow 造 PNG；存盘 `posts/{md5}/original.png`、preview==original、phash=None；md5 命中静默 `continue`。它注释明写 `# no pipeline yet`，是等本切片兑现的占位。存盘结构与本切片定稿的 `posts/{id}/` **冲突**。
- **环境**：hermes venv 已装 backend(editable) + Pillow 12.2.0；`imagehash` **未装**（实现阶段装，记入 `pyproject.toml` 依赖）。
- **测试基线**：当前 25 例全绿（7.32s）。

## 3. 范围

### In scope
- **`services/media.py`** —— 媒体处理内核（纯函数 + 摄入服务）：
  - `compute_md5(data: bytes) -> str`
  - `compute_phash(image: Image) -> str`（imagehash 的 `phash`，存 hex）
  - `make_thumbnails(image) -> tuple[bytes, bytes]`（thumb 150×150、preview 850×850，等比缩放）；动图取首帧做缩略图，原图保留动画
  - `ingest(db, data, *, source_site, source_id, source_url, file_ext, is_animated, rating) -> Post` —— 核心：md5 去重 → 落盘 → 写 Post（flush 拿 id → 建 `posts/{id}/` → 存 original/preview/thumb 相对路径 → 存 phash 字段 → commit）
- **`DuplicateError(AppError)`** —— md5 命中时抛（code `duplicate`，HTTP 409），让上层决定跳过还是别的。
- **迁移 `seed_dev.py`** —— 用 `media.ingest` 替换手搓路径，dev 数据成真缩略图 + 真 phash；目录结构改 `posts/{id}/`。
- **`tests/test_media.py`** —— 真图字节 fixture，端到端断言：落盘文件存在、Post 行字段正确、md5 去重抛 DuplicateError、phash 非空、缩略图尺寸正确。

### Out of scope
- phash **查邻标记 duplicate**（`duplicate_of_id`/`is_duplicate` 的赋值）—— 留给切片 4/8 的异步调度器（算 phash 值同步、查邻慢才异步）。
- 标签写入、implication 写时物化、`tag.post_count` 维护 —— 切片 2 剩余。
- 任何 API 端点、请求/响应 schema、任务调度（APScheduler）—— 切片 8。
- scraper、抓取器抽象 —— 切片 4。
- 删除/编辑 Post、`/next` 翻页上下文。

## 4. 验收标准

- [ ] **AC1 — ingest 落盘 + 写库**：给 PNG 字节流调 `ingest`，断言 `media/posts/{id}/{original,preview,thumb}.png` 三文件存在；Post 行的 `file_path/thumb_path/preview_path` 是相对 `media_dir` 的 `posts/{id}/...` 路径；`width/height/file_size/md5/rating` 正确。
- [ ] **AC2 — md5 精确去重**：同一字节流第二次 `ingest` 抛 `DuplicateError`（code `duplicate`），且**不产生第二条 Post 行、不重复落盘**。
- [ ] **AC3 — phash 同步计算并存字段**：ingest 后 `Post.phash` 非空（hex str），同一图缩放后 phash Hamming 距离小、完全不同图距离大（对照断言）。
- [ ] **AC4 — 缩略图尺寸**：thumb ≤ 150×150、preview ≤ 850×850（等比，取最长边）；动图（GIF）缩略图取首帧且为静态 PNG，原图保留动画（`is_animated` 正确）。
- [ ] **AC5 — seed_dev 迁移**：`python -m scripts.seed_dev` 用 `media.ingest` 造数；dev 库 Post 的 phash 非空、preview 是真缩略图（非等于 original）；目录结构 `posts/{id}/`。
- [ ] **AC6 — id 先有鸡先有蛋**：`ingest` 用 flush 拿 id 后再建目录落盘，落盘失败不产生半残 Post 行（事务回滚或落盘在 commit 前）。
- [ ] **AC7 — 回归**：`pytest -v` 全绿（原 25 + 新增 media 测试），`imagehash` 记入 `pyproject.toml`。

## 5. 约束

- 零 schema 变更（字段已齐，不加迁移）。
- `imagehash` 是唯一允许的新依赖（纯 Python，依赖 Pillow，无 C 扩展）。
- 路径一律存相对 `media_dir` 的字符串（便于迁移），落盘用 `settings.media_path` 绝对路径。
- 禁 `create_all`、禁 raw SQL、禁业务逻辑进 route（本切片本就无 route）、禁 `fav_count`。
- 摄入入口接受字节流而非文件路径（抓取器下载的是 bytes，本地导入读文件成 bytes 后喂入，统一接口）。
- `from __future__ import annotations` + 全函数签名类型注解 + `T | None` 联合。

## 6. 开放问题

无（核心决策已在切片选择阶段与用户敲定，见 design.md §3 决策记录）。
