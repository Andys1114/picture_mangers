# import 任务调度 + 进度端点 — 技术设计

> 配套 `prd.md`。APScheduler 后台调度 + scan_history 增量表 + 内存任务状态 + 取消。复用 scrape_to_db + media.ingest。

## 1. 模块边界

```
backend/app/models/scan_history.py     ← 新增：ScanHistory 模型
backend/app/models/__init__.py         ← 改：导出 ScanHistory
backend/alembic/versions/xxxx_add_scan_history.py  ← 新增：迁移
backend/app/services/tasks.py          ← 新增：调度内核（APScheduler + 任务状态 + 取消）
backend/app/services/import_service.py ← 新增：本地扫描编排（增量 + ingest）
backend/app/api/import_.py             ← 新增：import/tasks 端点（避免关键字 import）
backend/app/api/__init__.py            ← 改：挂 import_ router
backend/app/schemas/task.py            ← 新增：任务请求/响应模型
backend/app/main.py                    ← 改：启动 BackgroundScheduler
backend/tests/test_import_tasks.py     ← 新增
backend/pyproject.toml                 ← 改：加 apscheduler 依赖
```

**不碰**：`scrape.py`（只调 scrape_to_db）、`media.py`、`tags.py`、`search.py`、`post_edit.py`。

层级守约：`tasks.py`/`import_service.py` 不导入 fastapi；`api/import_.py` route 薄调 service。

## 2. 数据模型

### 2.1 `models/scan_history.py` — ScanHistory

```python
class ScanHistory(Base):
    """A file that has been scanned by a local import. Used to skip unchanged
    files on re-scan (mtime check) without re-reading bytes / re-computing md5."""
    __tablename__ = "scan_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    mtime: Mapped[float] = mapped_column(nullable=False)  # os.path.getmtime
    scanned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
```

迁移：新建表，可逆（downgrade drop table）。

### 2.2 任务状态（内存）

```python
@dataclass
class TaskState:
    task_id: str
    kind: str               # "scan" | "scrape"
    status: str             # "pending" | "running" | "completed" | "failed" | "cancelled"
    processed: int = 0
    total: int = 0
    duplicates: int = 0
    failed: int = 0
    error: str | None = None
    cancel_requested: bool = False
    started_at: datetime
    finished_at: datetime | None = None
```

存 `services/tasks.py` 模块级 `dict[str, TaskState]`，加 `threading.Lock` 保护（多任务并行写）。进程重启丢失（可接受）。

## 3. 调度内核（`services/tasks.py`）

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

_scheduler = BackgroundScheduler(executors={"default": ThreadPoolExecutor(max_workers=3)})
# main.py 启动时 _scheduler.start()

def submit_scan(path: str) -> str:
    """提交本地扫描任务，返回 task_id。"""
    task_id = secrets.token_hex(8)
    _tasks[task_id] = TaskState(task_id, "scan", "pending", started_at=now)
    _scheduler.add_job(_run_scan, args=[task_id, path], id=task_id)
    return task_id

def submit_scrape(query: str, limit: int) -> str:
    """提交抓取任务。"""
    ...  # 同上，调 _run_scrape

def get_task(task_id: str) -> TaskState | None: ...
def cancel_task(task_id: str) -> bool:
    """设置 cancel_requested 标志，任务循环检查退出。"""

def _run_scan(task_id, path):
    """后台线程：调 import_service.scan_directory，循环更新进度。"""
    state = _tasks[task_id]
    state.status = "running"
    import_service.scan_directory(task_id, path, state, _is_cancelled)
    state.status = "cancelled" if state.cancel_requested else "completed"
    state.finished_at = now

def _run_scrape(task_id, query, limit):
    """后台线程：调 scrape_to_db。"""
    ...  # 用 DanbooruScraper + scrape_to_db，更新进度
```

**取消**：`cancel_task` 设 `cancel_requested=True`，`_run_scan`/`_run_scrape` 循环检查 `state.cancel_requested` 退出。

**并发**：max_workers=3 允许 3 个任务同时 running。SQLite WAL 单写者，并行写 DB 串行等待（GIL + WAL 保证一致，无数据损坏）。

## 4. 本地扫描编排（`services/import_service.py`）

```python
def scan_directory(task_id, path, state, is_cancelled):
    """递归扫描 path，增量跳过未变文件，ingest 新文件。"""
    files = [递归收集 png/jpg/webp/gif/apng]
    state.total = len(files)
    db = SessionLocal()  # 后台线程独立 session
    try:
        for f in files:
            if is_cancelled(task_id): return
            # 增量：查 scan_history，stat mtime，跳过未变
            mtime = os.path.getmtime(f)
            hist = db.execute(select(ScanHistory).where(ScanHistory.path == f)).scalar_one_or_none()
            if hist and hist.mtime == mtime:
                state.processed += 1
                continue
            # 新/变文件：读 bytes + ingest
            try:
                data = Path(f).read_bytes()
                media.ingest(db, data, source_site="local", source_id=None,
                             source_url=None, file_ext=ext, is_animated=..., rating="safe")
                state.processed += 1
                # 更新 scan_history
                if hist: hist.mtime = mtime
                else: db.add(ScanHistory(path=f, mtime=mtime))
                db.commit()
            except DuplicateError:
                state.duplicates += 1
                state.processed += 1
            except Exception:
                state.failed += 1
                state.processed += 1
    finally:
        db.close()
```

**关键**：后台线程用独立 `SessionLocal()`（不与请求 session 共享）。每个文件处理后 commit（进度持久化 + scan_history 更新）。

## 5. 端点设计（`api/import_.py`）

全部 `/api` 前缀，需认证。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/import/scan` | body `{path}` → `{task_id}` |
| POST | `/api/import/scrape` | body `{query, source:'danbooru', limit}` → `{task_id}` |
| GET | `/api/tasks/{task_id}` | → TaskStatusResponse |
| POST | `/api/tasks/{task_id}/cancel` | → `{cancelled: bool}` |

文件名 `import_.py`（避免 Python 关键字 `import`）。

## 6. Pydantic schemas（`schemas/task.py`）

```python
class ScanRequest(BaseModel):
    path: str = Field(min_length=1)

class ScrapeRequest(BaseModel):
    query: str = Field(min_length=1)
    source: str = Field(default="danbooru", pattern=r"^danbooru$")
    limit: int = Field(default=20, ge=1, le=1000)

class TaskCreateResponse(BaseModel):
    task_id: str

class TaskStatusResponse(BaseModel):
    task_id: str
    kind: str
    status: str
    processed: int
    total: int
    duplicates: int
    failed: int
    error: str | None = None

class TaskCancelResponse(BaseModel):
    cancelled: bool
```

## 7. 决策记录

| # | 决策 | 依据 |
|---|---|---|
| D1 | APScheduler BackgroundScheduler | 用户拍板。design §4 提了；线程池管理 + add_job 抽象。max_workers=3 支持多任务并行。 |
| D2 | scan_history 表增量 | 用户拍板。design §4 明确「记录已扫描路径+mtime」。stat mtime 跳过未变，避免重读 bytes。 |
| D3 | 多任务并行（max_workers=3） | 用户拍板。SQLite WAL 单写者并行写串行等待，但启动不阻塞。 |
| D4 | 任务取消做 | 用户取完整方案。cancel_requested 标志 + 循环检查。 |
| D5 | scrape 测 FakeScraper 注入 | 复用 test_scrape 模式，不靠真实网络（Cloudflare 403）。 |
| D6 | 任务状态内存 dict | design §4「内存够用」。重启丢失可接受。 |
| D7 | 后台线程独立 SessionLocal | 不与请求 session 共享，避免跨线程 session 误用。 |

## 8. 测试设计（`tests/test_import_tasks.py`）

挑战：后台任务异步，测试要等完成。用轮询等 task 完成(sleep + 查 status)。

- `test_scan_end_to_end`（AC2+AC3）：tmp 目录造几个 PNG → POST /import/scan → 轮询 GET /tasks/{id} 到 completed → 断言 post 入库 + scan_history 记录 + 进度数对。
- `test_scan_incremental`（AC2）：二次扫描同一目录，stat mtime 跳过，processed=total 但 ingest 不重调（查 scan_history mtime 未变）。
- `test_scrape_with_fake_scraper`（AC4）：monkeypatch DanbooruScraper 或注入 FakeScraper 到 submit_scrape → 任务完成 + 进度。
- `test_task_cancel`（AC5）：提交长任务 → POST /cancel → 轮询到 cancelled。
- `test_concurrent_tasks`（AC6）：同时提交 2 个 scan → 两者都进 running。
- `test_auth`（AC7）：所有端点 401 未登录。

**测试要 patch BackgroundScheduler**：用同步执行（max_workers=1 或 mock add_job 直接调函数）避免异步测试复杂。或用 `time.sleep` 轮询。

## 9. 兼容性 / 回滚

- scan_history 迁移可逆（downgrade drop table）。
- APScheduler 启动在 main.py；回滚删启动代码 + 依赖即可。
- 任务状态内存，回滚无 DB 影响。
- 复用 scrape_to_db/media.ingest 不改，向后兼容。

## 10. 风险

- **后台线程 DB session**：必须独立 SessionLocal，不能跨线程共享请求 session。每个文件 commit 避免长事务。
- **测试异步**：后台任务难测。方案：patch scheduler 同步执行，或轮询 sleep。倾向 patch 同步（测试快、确定）。
- **APScheduler 进程退出**：BackgroundScheduler 非守护线程可能阻塞进程退出。main.py shutdown 需调 `_scheduler.shutdown(wait=False)`。
- **SQLite 并行写**：WAL 单写者，并行任务写 DB 会串行等待，可能超时。设 timeout 重试或接受等待。
