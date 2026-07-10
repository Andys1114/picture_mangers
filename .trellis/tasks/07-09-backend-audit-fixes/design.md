# 技术设计：后端审计修复

## 总体思路

41 条按「文件所有权」切成 5 个互不重叠的工作包（W1–W5），并行实现互不冲突；每包自带回归测试；最后全量测试 + 按包对抗复核。

## 工作包与文件所有权（严格边界，禁止越界改文件）

### W1 导入/抓取任务链（services/import_service.py、services/scrape.py、services/tasks.py、schemas/task.py、api/import_.py；测试 tests/test_import_tasks.py、tests/test_scrape.py）

- #1/#2/#7（高，同根因）：`scan_directory` 与 `scrape_to_db` 的每个 `except DuplicateError/Exception` 分支加 `db.rollback()`。
- #8（中）：DuplicateError 分支同样写入/更新 scan_history（提取 `_record_scan_history(db, path, mtime)` 公共函数），文件未变时重扫不再重读。
- #12/#13（中，同根因）：`scrape_to_db(db, scraper, query, limit, state=None, is_cancelled=None)` 扩展签名（默认 None 保持旧调用兼容）；search 返回后 `state.total = len(posts)`，循环每帖 `state.processed += 1`，循环开头 `if is_cancelled and is_cancelled(): return result`；tasks.py `_run_scrape` 传入 state 与取消回调（对齐 `_run_scan`）。
- #26/#27（低，同根因）：文件清单阶段 `p.stat()` 包 try/except OSError（辅助函数返回 None 则跳过该文件）。
- #28（低）：所有逐文件/逐帖 `except` 分支加 `logger.warning("ingest failed path=%s err=%s", ...)`（scrape 侧记 source_id）。
- #29（低）：`ScanRequest.path` 加 `max_length=1024`，`ScrapeRequest.query` 加 `max_length=512`。
- #34（低）：`submit_scan`/`submit_scrape` 在 `_tasks_lock` 内查重：已存在同 kind+参数且 status ∈ {pending, running} 的任务直接返回旧 task_id（TaskState 增加 params 字段）。
- #35（低）：`shutdown_scheduler` 先遍历 `_tasks` 置 `cancel_requested=True` 再 `shutdown(wait=False)`。
- #36（低）：任务失败 `logger.exception(...)`，`state.error` 存通用中文提示（「导入失败，请查看服务器日志」/「抓取失败，请查看服务器日志」），不再放 str(exc)。
- 日志点（#39 的本包部分）：任务 started/finished/failed 记 INFO/ERROR。

### W2 帖子编辑与标签服务（services/post_edit.py、services/tags.py；测试 tests/test_post_edit.py、tests/test_tags.py）

- #3（高）：`update_post` 计算 `to_remove` 前用 `tags.closure_of(db, list(target_ids))` 展开：`to_remove = current_after_add - closure_of(...)`，保住 implication 后件。
- #4（高）:`delete_post` 在 `db.delete(post)` 前查该 post 的 post_tags，逐 tag `post_count -= 1`（clamp ≥ 0）。
- #9（中）：`tag_post`（及内部提交路径）增加 `commit: bool = True` 参数；`update_post` 调用 `commit=False`，全函数单事务、最后统一 commit；异常时 rollback，杜绝「并集中间态」。
- #32（低）：标签 get-or-create 的 `db.flush()` 捕获 IntegrityError → rollback 后重查一次（tags.py 与 post_edit.py 两处同模式）。注意 #9 改单事务后 rollback 会波及未提交改动——重查逻辑要在冲突后重建本次事务所需状态或直接抛 ConflictError，实现时二选一并写清楚（单用户场景允许简化为「重试一轮 get」）。
- #33（低）：`create_implication` 回填改为一次 `select(PostTag.post_id, PostTag.tag_id).where(post_id.in_(affected))` 建 dict，Tag 对象按 new_closure 预取复用，post_count 聚合一次更新。

### W3 媒体写入/抓取器/基础设施（services/media.py、scrapers/base.py、scrapers/danbooru.py、db.py、config.py、pyproject.toml、tests/conftest.py；测试 tests/test_media.py 及新增 tests/test_scrapers.py 可选）

- #6（中）：`media.ingest` 开头校验 file_ext ∈ 图片白名单（对齐 SUPPORTED_EXTS 的无点小写集合），不合法抛 ValidationError；`danbooru._parse_post` 同步收敛。
- #14（中）：`_set_sqlite_pragma` 加 `PRAGMA busy_timeout=30000`；conftest.py 的镜像 pragma 同步加（conftest 归本包所有）。
- #15（中）：`httpx>=0.26` 移入 `[project].dependencies`（dev 里可删）。
- #24（低）：`Scraper.download` 前校验 `urlparse(image_url)`：scheme 必须 https、host 匹配站点白名单（Scraper 类属性 `allowed_hosts`，Danbooru 为 `*.donmai.us`）；`follow_redirects=False`，手动跟随重定向（≤3 跳）且每跳重新校验。
- #25（低）：下载改 `httpx.stream` 分块读，累计超过 200MB（模块常量 `MAX_DOWNLOAD_BYTES`，注释注明与 import_service.MAX_FILE_BYTES 对齐）即抛 ScraperError。
- #41（低）：删除 config.py 的 `secret_key` 字段（全项目零消费者）。
- 日志点（#39 本包部分）：scraper 429/5xx 重试记 WARNING。

### W4 认证与会话（api/auth.py、services/auth.py、schemas/auth.py、deps.py；测试 tests/test_auth.py）

- #18（低）：`create_user` 固定 `User(id=1, ...)`；捕 IntegrityError → rollback → ConflictError（顺序第二次 setup 仍 409，并发也被主键闭合）。
- #19（低）：`_COOKIE_KWARGS` 加 `"max_age": settings.session_expire_days * 86400`。
- #20（低）：/setup 改 `status.HTTP_201_CREATED`。
- #21（低）：services/auth.py 新增 `set_safe_mode(db, session_row, value)`，update_settings 路由只调用它。
- #22（低）：`validate_session`/`get_session_row` 命中过期行时 `db.delete(row); db.commit()` 再返回 None。
- #23（低）：SetupRequest/LoginRequest 加 validator：`len(password.encode("utf-8")) > 72` → ValueError（中文提示「密码过长：最多 72 字节」）。
- #40（低，本包部分）：deps.py 与 api/auth.py 统一改 `from app.models.user import Session as SessionRow, User`（与 services/auth.py 现有别名一致）；`db: Session` 一律指 sqlalchemy.orm.Session，会话行注解用 SessionRow。
- 日志点（#39 本包部分）：登录成功/失败记 INFO（不含密码）。

### W5 主应用/媒体路由/收藏/模型迁移（main.py、api/posts.py、api/tags.py、api/favorites.py、services/favorites.py、services/search.py、services/errors.py、schemas/post.py、models/post.py、models/favorite.py、alembic/versions/*、frontend/lib/types.ts；测试 tests/test_posts.py、tests/test_favorites.py、tests/test_schema.py、新增 tests/test_media_route.py）

- #5（中）+ #17（低）：移除 `app.mount("/media", StaticFiles...)`，改认证路由 `GET /media/{path:path}`：依赖 `get_current_session`，`(media_dir / path).resolve()` 后 `is_relative_to(media_dir)` 防穿越，FileResponse 加 `Cache-Control: public, max-age=31536000, immutable`；URL 形状不变。
- #10/#31（中，同根因）：services/favorites.py 新增 `favorite_post_ids(db, post_ids) -> set[int]`（默认收藏夹不存在返回空集）；api/posts.py list/detail/patch 三处按成员关系填充 favorite，删除过时注释。
- #11（中）：Alembic 迁移给 favorites.name 加 UNIQUE（batch 模式；先把重名行改成 `name-id` 去重）；`create_favorite` 查重抛 ConflictError(409)；`get_or_create_default` 改 `.scalars().first()` 兜底。
- #16（低）：main.py 注册 `RequestValidationError` 处理器（实现放 services/errors.py），转统一信封 `{"error":{"code":"validation_error","message":<拼接可读消息>}}`，状态码 422。
- #30（低）：`search.get_post` 加 `safe_mode` 参数（safe_mode 且 rating != 'safe' 时抛 NotFoundError）；`next_post` 加 safe_mode 过滤（补 `Post.rating == 'safe'` 条件，更新过时 docstring）；get_post/next 路由改依赖 `get_current_session`。
- #37（低）：TagResponse 加 `is_deprecated: bool = False`；frontend/lib/types.ts 的 Tag 加 `is_deprecated: boolean`。
- #38（低）：models 加 `ix_posts_rating`、`ix_posts_duplicate_of_id`、`ix_favorite_items_post_id`，与 #11 合并出一条迁移（先 `alembic history` 确认当前 head 再挂 down_revision）。
- #39（低，收口）：main.py 加 `logging.basicConfig(level=logging.INFO, ...)`；services/errors.py 的 `unhandled_exception_handler` 加 `logger.exception(...)`。
- #40（低，本包部分）：api/posts.py 的 Session 遮蔽改法同 W4（SessionRow 别名）。

## 关键取舍

- **/media 认证**：StaticFiles 不支持依赖注入，改 APIRouter + FileResponse 是最小可行改法；图片场景不需要 Range 支持。未登录 `<img>` 显示破图可接受（前端登录态下才渲染画廊）。
- **bcrypt 72 字节**：选 schema 校验拒绝而非 sha256 预哈希——预哈希会让既有用户的存量 hash 失效。
- **#9 单事务化**：`tag_post` 加 `commit=True` 默认参数保持旧调用方兼容，只有 `update_post` 传 False。
- **#34 去重**：返回旧 task_id 而非报错，前端无需改动。
- **迁移**：一条迁移同时做 favorites.name 去重+UNIQUE 和三个索引，减少版本碎片；downgrade 全部可逆（去重改名不回滚）。

## 测试运行方式

```
cd backend && ./.venv/Scripts/python -m pytest -q
```

conftest 每例建临时 SQLite 并 `alembic upgrade head`，迁移正确性由全量测试兜底。
