# import 任务调度 + 进度端点 — 执行计划

> 配套 `prd.md` + `design.md`。按序执行，每步带校验门。

## 0. 前置（task.py start 前已完成）
- [x] prd.md（8 条 AC，无开放问题）
- [x] design.md（10 节：边界/数据模型/调度内核/扫描编排/端点/schemas/决策7条/测试/回滚/风险）
- [x] implement.md（本文件）

## 1. scan_history 模型 + 迁移

- [ ] **1.1** `backend/app/models/scan_history.py`：ScanHistory(id/path unique/mtime/scanned_at)。
- [ ] **1.2** `backend/app/models/__init__.py` 导出 ScanHistory。
- [ ] **1.3** `alembic revision --autogenerate -m "add scan_history"` → 审查迁移 → 确认可逆。
  - **校验门**：`alembic upgrade head` + `alembic downgrade -1` + `upgrade head` 成功。

## 2. schemas/task.py

- [ ] **2.1** `backend/app/schemas/task.py`：ScanRequest/ScrapeRequest/TaskCreateResponse/TaskStatusResponse/TaskCancelResponse（design §6）。
- [ ] **2.2** `schemas/__init__.py` 导出。
  - **校验门**：`python -c "from app.schemas.task import TaskStatusResponse"`。

## 3. services/tasks.py —— 调度内核

- [ ] **3.1** TaskState dataclass + 模块级 `_tasks` dict + `_tasks_lock`。
- [ ] **3.2** BackgroundScheduler 单例(max_workers=3) + start/shutdown 钩子。
- [ ] **3.3** submit_scan/submit_scrape/get_task/cancel_task。
- [ ] **3.4** `_run_scan`/`_run_scrape` 后台函数（调 import_service/scrape_to_db，循环更新进度 + 检查取消）。
  - **校验门**：`python -c "from app.services.tasks import submit_scan, get_task, cancel_task"`。

## 4. services/import_service.py —— 本地扫描

- [ ] **4.1** `scan_directory(task_id, path, state, is_cancelled)`：递归收集 → stat mtime 查 scan_history 跳过 → 读 bytes → media.ingest → 更新 scan_history + 进度。
- [ ] **4.2** 后台线程独立 SessionLocal + 每文件 commit。
  - **校验门**：`python -c "from app.services.import_service import scan_directory"`。

## 5. api/import_.py + main.py 启动

- [ ] **5.1** `backend/app/api/import_.py`：POST /import/scan、POST /import/scrape、GET /tasks/{id}、POST /tasks/{id}/cancel，全认证 route 薄调 service。
- [ ] **5.2** `backend/app/api/__init__.py` 挂 import_ router。
- [ ] **5.3** `backend/app/main.py`：启动 BackgroundScheduler + shutdown 钩子。
- [ ] **5.4** `backend/pyproject.toml` 加 `apscheduler>=3.10`。
  - **校验门**：`python -c "from app.main import app; print([r.path for r in app.routes if '/import' in r.path or '/tasks' in r.path])"`。

## 6. tests/test_import_tasks.py

- [ ] **6.1** fixture：patch BackgroundScheduler 同步执行（或 max_workers=1 + 轮询）。
- [ ] **6.2** `test_scan_end_to_end`（AC2+AC3）。
- [ ] **6.3** `test_scan_incremental`（AC2 二次跳过）。
- [ ] **6.4** `test_scrape_with_fake_scraper`（AC4）。
- [ ] **6.5** `test_task_cancel`（AC5）。
- [ ] **6.6** `test_concurrent_tasks`（AC6）。
- [ ] **6.7** `test_auth`（AC7）。
  - **校验门**：`cd backend && python -m pytest tests/test_import_tasks.py -v` 全绿。

## 7. 全量回归 + spec 自查

- [ ] **7.1** `cd backend && python -m pytest -v` → 原 57 + 新 import_tasks 测试全绿。
- [ ] **7.2** spec 自查：复用 scrape_to_db/media.ingest、route 薄调 service、scan_history 迁移可逆、后台线程独立 session、APScheduler 依赖记入 pyproject。

## 校验命令汇总

```bash
cd backend
python -m pytest -v                                    # 全量（7.1）
python -m pytest tests/test_import_tasks.py -v         # 仅 import（6.7 后）
python -m alembic upgrade head && python -m alembic downgrade -1 && python -m alembic upgrade head  # 1.3
```

## 回滚点

- **步骤 1 后**：删 scan_history 模型 + 迁移 downgrade，DB 无影响。
- **步骤 3-4 后**：删 tasks.py + import_service.py，DB 无影响。
- **步骤 5 后**：删 import_.py + main.py 启动代码 + pyproject 依赖，端点消失。
- **全切片回滚**：`alembic downgrade -1` 撤 scan_history + `git revert`。

## 风险点（来自 design §10）

- 后台线程 DB session 必须独立（不共享请求 session）。
- 测试异步：patch scheduler 同步执行优先。
- APScheduler shutdown：main.py 需 shutdown 钩子避免阻塞进程退出。
- SQLite 并行写：WAL 单写者串行等待，可能超时。
