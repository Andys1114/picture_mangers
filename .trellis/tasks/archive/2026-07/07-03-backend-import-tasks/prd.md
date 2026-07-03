# import 任务调度 + 进度端点 (切片8后端) — PRD

> 父任务：`06-28-gallery-app`（design.md §4 后台任务调度 + §6 import 端点）。后端最后一块，接已交付的 scrape_to_db + media.ingest。

## 1. Goal / 用户价值

把后端从「同步摄入服务」推进到「异步任务 + 进度可查」。交付后，前端导入页（切片8 UI）能启动本地扫描/抓取任务、轮询进度（已处理/总数/重复/失败）、看任务完成。核心是后台线程跑长任务不阻塞 API + 内存任务状态。

## 2. 已确认事实（来自 codebase/spec/网络探测）

- **父 design.md §4 后台任务调度**：「抓取/导入是长任务，走后台线程池不阻塞 API。任务状态存内存（单机够用），前端轮询 /api/tasks/{id} 看进度。」
- **父 design.md §4 本地导入路径 A**：递归扫描指定文件夹，支持 png/jpg/webp/gif/apng；**增量扫描**（记录已扫描路径 + mtime，二次只处理新文件）；本地图**无标签**，导入后手动打；进度反馈「已处理 X/Y，重复 N」。
- **父 design.md §6 import 端点**：`POST /api/import/scan {path}` → `{task_id}`；`POST /api/import/scrape {query, source, limit}` → `{task_id}`；`GET /api/tasks/{id}` → 进度（processed/total/duplicates）。
- **复用已就位**：
  - `services/scrape.py:scrape_to_db(db, scraper, query, limit)` —— 抓取编排（两阶段去重 + ingest + tag_post，返回 ScrapeResult）。
  - `services/media.py:ingest(db, data, ...)` —— 本地导入读文件成 bytes 喂它（md5 去重 + 缩略图 + phash）。
  - `scrapers/danbooru.py:DanbooruScraper` —— 抓取器（Cloudflare 403，真实不可行但代码就位）。
- **spec**：业务逻辑不在 route、AppError 子类、类型注解。
- **环境**：无 APScheduler（未装）；threading 标准库自带。
- **网络**：Danbooru Cloudflare 403，真实抓取不可行，scrape 任务测试靠 mock 或只测本地扫描。

## 3. 范围

### In scope
- **`models/scan_history.py`** + Alembic 迁移 —— scan_history 表(id/path/mtime/scanned_at, path unique)，记已扫描文件 mtime 做增量。
- **`services/tasks.py`** —— 任务调度内核：APScheduler BackgroundScheduler(max_workers=3) + 内存任务状态(dict[task_id, TaskState]) + 进度查询 + 取消标志。
- **`services/import_service.py`** —— 本地扫描编排：递归扫文件夹 → stat mtime 查 scan_history 跳过未变 → 读 bytes → media.ingest(md5 去重) → 更新 scan_history → 进度更新。
- **`api/import.py`** —— POST /import/scan、POST /import/scrape、GET /tasks/{id}、POST /tasks/{id}/cancel。
- **`schemas/task.py`** —— TaskCreateResponse(task_id)、TaskStatusResponse(status/processed/total/duplicates/failed)。
- **`tests/test_import_tasks.py`** —— 本地真文件扫描(端到端) + FakeScraper 注入测 scrape + 取消 + 并发。

### Out of scope
- 前端导入页 UI（切片8 前端）。
- 任务持久化（重启丢失，内存够用）。
- 定时/cron 调度（本切片只做手动触发的一次性任务）。
- gelbooru/moebooru（已排除）。

## 4. 验收标准

- [ ] **AC1 — scan_history 迁移**：新表 scan_history(path unique + mtime + scanned_at) 建成，迁移可逆。
- [ ] **AC2 — 本地扫描端到端**：POST /import/scan {path} → 返回 task_id → 后台递归扫 → 新文件 ingest 入库 + scan_history 记 mtime → 二次扫描 stat mtime 跳过未变(ingest 不重调)。
- [ ] **AC3 — 扫描进度**：GET /tasks/{id} 返回 status(running/completed/failed/cancelled) + processed/total/duplicates/failed。
- [ ] **AC4 — 抓取任务**：POST /import/scrape {query, limit} → task_id → 后台调 scrape_to_db(用 DanbooruScraper) → 进度。Cloudflare 403 下真实抓取不可行,端点逻辑就位即可。
- [ ] **AC5 — 任务取消**：POST /tasks/{id}/cancel → 任务循环检查标志退出 → status=cancelled。
- [ ] **AC6 — 多任务并行**：同时提交 2 个任务,两者都进 running(BackgroundScheduler 线程池),不互相阻塞启动。
- [ ] **AC7 — 认证 + 不阻塞**：所有端点 401 未登录；POST 启动立即返回 task_id 不等任务完成。
- [ ] **AC8 — 回归**：`pytest -v` 全绿（原 57 + 新增 import_tasks 测试）；spec 自查（复用 scrape_to_db/media.ingest、route 薄调 service、scan_history 迁移可逆）。

## 5. 约束

- **schema 变更**：新增 scan_history 表 + Alembic 迁移（可逆）。
- 复用 scrape_to_db + media.ingest，不重写。
- APScheduler BackgroundScheduler(max_workers=3)，一次性 add_job（非 cron）。
- 任务状态内存 dict（重启丢失，可接受）。
- `from __future__ import annotations` + 类型注解 + 业务逻辑不在 route + 端点需认证。
- 后台线程不阻塞 API（POST 启动后立即返回 task_id）。

## 6. 开放问题

1. ~~调度实现~~：**APScheduler**（apscheduler 3.11.3 已装）。BackgroundScheduler 线程池跑一次性长任务。
2. ~~本地增量扫描~~：**scan_history 表**。建表记 path+mtime+scanned_at，扫描时 stat mtime 跳过未变文件。**需 Alembic 迁移**。
3. ~~任务并发~~：**多任务并行**（BackgroundScheduler 线程池 max_workers=3）。SQLite WAL 单写者，并行任务写 DB 会串行等待（可接受，GIL + WAL 保证一致）。
4. ~~任务取消~~：**做**。`POST /api/tasks/{id}/cancel` 设置取消标志，任务循环检查退出。
5. ~~scrape 测试~~：**FakeScraper 注入**。测 scrape 端点编排（复用 test_scrape 的 FakeScraper 模式），不靠真实网络。

无开放问题（5 个边界问题全敲定，均取完整方案）。
