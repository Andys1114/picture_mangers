# 后端审计报告（只读检查，未改代码）

> 日期：2026-07-04 · 方式：多智能体审计（8 维度并行扫描 + 按文件对抗复核，27 个智能体）
> 结果：原始 45 条 → 确认 **41** 条（高 4 / 中 11 / 低 26）/ 否决 4 条
> 基线：backend 63 个测试全绿（但均未覆盖下列场景）。威胁模型：单用户本地/局域网部署。

## 目录（按严重度）

1. [高] **transaction-boundaries** — services/import_service.py:89 — ingest 失败后不 rollback，脏 session 里的半成品 Post 行会被下一个文件的 commit 顺
2. [高] **dirty-session-after-ingest-failure** — services/import_service.py:89 — 扫描循环捕获 ingest 异常后不 rollback，脏 session 会把半成品 Post 随下一个文件的 com
3. [高] **implication-materialization-consistency** — services/post_edit.py:78 — PATCH 全量替换标签会把刚物化出来的 implication 后件立刻删掉，破坏 ADR-0001「post_tag
4. [高] **cascade-delete** — services/post_edit.py:111 — 删除 post 时 post_tags 由 FK CASCADE 静默删除，Tag.post_count 不递减，计数永
5. [中] **unauthenticated-media-mount** — main.py:30 — /media 静态目录整体挂载且不经任何认证，图片可被局域网内任何人直接拉取，也完全绕过 safe_mode 过滤
6. [中] **path-traversal** — services/media.py:170 — ingest 的 file_ext 未做白名单/字符校验就拼进写盘文件名，抓取链路的上游 JSON 可注入路径分隔符实现
7. [中] **apscheduler-worker-session-exception-handling** — services/import_service.py:89 — worker 循环里捕获 ingest 异常后不 rollback，脏 session 使后续所有文件的查询抛 Pend
8. [中] **rescan-rereads-duplicates** — services/import_service.py:87 — DuplicateError 分支不写 scan_history，重复文件在每次重扫时都被完整读入内存并重算 md5
9. [中] **transaction-boundaries** — services/post_edit.py:69 — update_post 不是原子操作：tags.tag_post 在中途 commit，rating+新增标签先落库，之
10. [中] **schema-field-consistency** — api/posts.py:36 — PostSummary/PostDetail 的 favorite 字段永远硬编码 False，但收藏 API 已实现并
11. [中] **unique-constraints-races** — services/favorites.py:72 — Favorite.name 无唯一约束，默认收藏夹按名字识别；重名后 get_or_create_default 的 s
12. [中] **cancel-requested-cooperative-cancel-window** — services/tasks.py:161 — scrape 任务的取消完全无效：整个抓取批次跑完之前从不检查 cancel_requested，进度也全程 0/0
13. [中] **task-progress-granularity** — services/tasks.py:162 — scrape 任务的进度只在整批结束后一次性写入，且 scrape 循环从不轮询取消标志——进度端点全程显示 0/0，取
14. [中] **sqlite-wal-busy-timeout-long-transaction** — db.py:33 — 未配置 busy_timeout，且 ingest 在持有写事务期间做磁盘文件 IO，多 worker 并发时易触发 d
15. [中] **pyproject-deps-mismatch** — pyproject.toml:7 — httpx 在运行时代码中被 import，但只声明在 dev 可选依赖里，生产安装缺依赖
16. [低] **error-envelope-coverage** — main.py:33 — Pydantic/FastAPI 的 422 校验错误未接入统一错误信封，返回 {"detail":[...]}，违反 
17. [低] **media-cache-control** — main.py:30 — /media 用裸 StaticFiles 挂载，不发 Cache-Control——画廊每次渲染都对每张缩略图发条件请
18. [低] **setup-endpoint-race** — api/auth.py:48 — /setup 的 has_user 检查与 create_user 非原子，并发首次创建时两个不同用户名的请求可同时通过
19. [低] **cookie-lifetime-mismatch** — api/auth.py:30 — set_cookie 未设 max_age/expires，cookie 是浏览器会话级，而服务端 session 有效
20. [低] **status-code-semantics** — api/auth.py:45 — POST /api/auth/setup 创建用户资源却显式返回 200，而项目内其他创建端点（tags/favorit
21. [低] **spec-thin-routes** — api/auth.py:93 — update_settings 路由内直接改 ORM 字段并 commit（业务持久化逻辑写在 api/ 层），违反 d
22. [低] **expired-session-cleanup** — services/auth.py:65 — 过期会话行只在读取时被判定为无效，从不物理删除；除显式 /logout 外没有任何清理机制，sessions 表随时间只
23. [低] **bcrypt-72-byte-truncation** — services/auth.py:25 — bcrypt 静默截断 72 字节以后的密码内容，超长密码的尾部不参与校验；算法与 cost=12 本身合格，仅此边界未
24. [低] **scraper-ssrf** — scrapers/base.py:102 — Scraper.download 对 image_url 无 scheme/host 校验，上游 JSON 可指挥后端向
25. [低] **download-size-limit** — scrapers/base.py:106 — 抓取下载无大小上限，resp.content 一次性读入内存；本地导入的 200MB 上限（import_service
26. [低] **scan-filesystem-race-stat** — services/import_service.py:51 — 构建文件清单时 p.stat() 无异常保护，扫描期间文件被删除/占用会让整个任务直接 failed
27. [低] **scan-walk-fragility-and-memory** — services/import_service.py:51 — 扫描前置阶段在列表推导内对每个文件 p.stat()，文件在遍历期间被删除/无权限会抛 OSError 使整个任务直接 
28. [低] **spec-error-handling-silent-swallow** — services/import_service.py:89 — 扫描/抓取的逐文件 `except Exception:` 只做计数不记日志，违反 error-handling「ser
29. [低] **schema-length-bounds** — schemas/task.py:8 — ScanRequest.path 与 ScrapeRequest.query 无 max_length，超长字符串会被原
30. [低] **safe-mode-coverage** — api/posts.py:64 — safe_mode 只在列表注入，详情 GET /posts/{id} 与 /posts/{id}/next 完全不过滤
31. [低] **spec-quality-stale-docstring** — api/posts.py:36 — favorite 字段在 list/detail/patch 三处硬编码 False，注释「favorites API 
32. [低] **unique-constraints-races** — services/tags.py:214 — tag_post/update_post 的标签 get-or-create 是先查后插，后台导入线程与前台 PATCH
33. [低] **n-plus-one** — services/tags.py:300 — create_implication 回填对每个受影响 post 单独 SELECT 其 post_tags，再逐 ta
34. [低] **duplicate-task-submission-dedup** — services/tasks.py:83 — 同一路径/同一 query 可重复提交并发任务，无任何去重，两个 worker 同时扫同一目录互相制造 Integrit
35. [低] **scheduler-shutdown-inflight-tasks** — services/tasks.py:71 — shutdown 时只 shutdown(wait=False)，不给在途任务广播 cancel_requested；非
36. [低] **spec-error-handling** — services/tasks.py:137 — 任务失败时把 str(exc) 原样放进 API 响应，违反 quality-guidelines 明令禁止的「Retu
37. [低] **schema-field-consistency** — api/tags.py:35 — tags API 组装响应时传入 is_deprecated，但 TagResponse schema 没有该字段，Py
38. [低] **missing-index** — models/post.py:43 — posts.rating 与 duplicate_of_id 无索引，safe_mode 下每次列表的 COUNT 全表
39. [低] **spec-logging-guidelines** — services/errors.py:73 — 整个 backend/app 没有任何 logging 调用；logging-guidelines 要求的日志点（cat
40. [低] **spec-type-hints** — deps.py:8 — `from app.models.user import Session, User` 遮蔽了上一行导入的 sqlalc
41. [低] **config-dead-default-secret** — config.py:30 — secret_key 有弱默认值 "dev-secret-change-me" 但全项目零处使用，属误导性死配置

---

## 1. [高] transaction-boundaries · backend/app/services/import_service.py:89

**问题**：ingest 失败后不 rollback，脏 session 里的半成品 Post 行会被下一个文件的 commit 顺带提交（scrape.py 同模式）

**证据**：import_service.py:89-90 `except Exception: state.failed += 1` 无 db.rollback()；media.py:164-172 `db.add(post); db.flush()` 之后才写磁盘文件；import_service.py:97 下一个成功文件执行 `db.commit()`。

**触发场景**：扫描目录时某文件在 media.ingest 的 flush 之后写 original/preview 时抛 OSError（磁盘满/权限）：Post 行已 add+flush 且 file_path=""，异常被吞、未回滚；处理下一个文件成功后 db.commit() 把这条 file_path 为空的坏 Post 提交入库，画廊出现 404 图。若 flush 本身抛 IntegrityError 则 session 进入 PendingRollback，后续所有文件全部计入 failed。

**最小修复**：在 scan_directory 与 scrape_to_db 的每个 except 分支（含 DuplicateError 之外的 Exception）里加 db.rollback()；media.ingest 内部失败时也可自行 rollback 后再 raise。

**复核意见**：证据全部属实：media.py:164-165 add+flush 后才写文件（:170-172），import_service.py:89-90 捕获 Exception 不 rollback，line 97 下一个文件的 db.commit() 会把 file_path='' 的孤儿 Post 一并提交。ingest 的 docstring（media.py:114-116）明确把回滚责任交给调用方 session 生命周期，而 scan 的长活 worker session 恰好不满足该假设；test_media.py:253 也证明必须显式 rollback 才能丢弃该行。无测试覆盖此场景（test_import_tasks.py 只测成功/跳过路径）。数据损坏级正确性 bug，high 成立。

## 2. [高] dirty-session-after-ingest-failure · backend/app/services/import_service.py:89

**问题**：扫描循环捕获 ingest 异常后不 rollback，脏 session 会把半成品 Post 随下一个文件的 commit 一起提交，或让后续所有文件因 PendingRollbackError 全部失败

**证据**：import_service.py:87-97: `except DuplicateError: ... except Exception: state.failed += 1` 后无 db.rollback()；而 media.py:164-172 ingest 内先 `db.add(post); db.flush()` 再写文件。若 write_bytes 抛 OSError，session 里残留 file_path='' 的 Post，下一个成功文件走到 import_service.py:97 `db.commit()` 时一并提交

**触发场景**：扫描目录中某文件在 Pillow 解码成功但磁盘写入失败（磁盘满/路径被占用），或 commit 抛 IntegrityError：该 Post 已 add+flush 但未提交 → 异常被吞、无 rollback → 下一个文件 commit 时把 file_path 为空串的孤儿 Post 写进库（画廊出现打不开的图）；若是 commit 阶段异常则后续每个文件都 PendingRollbackError，整批标 failed

**最小修复**：在 scan_directory 的 `except Exception:` 分支加 `db.rollback()`（DuplicateError 分支也加一句无害）；或在 media.ingest 内 try/except 包住文件写入并 rollback 后重抛

**复核意见**：与 #1 完全重复（同一 line 89、同一证据、同一场景的两条报告）。事实成立，理由同 #1；建议与 #1 合并为一条修复：except 分支加 db.rollback()。

## 3. [高] implication-materialization-consistency · backend/app/services/post_edit.py:78

**问题**：PATCH 全量替换标签会把刚物化出来的 implication 后件立刻删掉，破坏 ADR-0001「post_tags 恒为展开闭包」不变量

**证据**：post_edit.py:64 `target_ids = {tid for tid, _ in target}`（只含直接标签）；:69 `tags.tag_post(db, post_id, to_add)`（写入闭包，含后件）；:78 `to_remove = current_after_add - target_ids` 随后把闭包成员全部删除。

**触发场景**：存在 implication miku→vocaloid。PATCH /api/posts/{id} body={"tags":["miku"]}：tag_post 先写入 {miku, vocaloid}，随后 to_remove={vocaloid} 把 vocaloid 行删掉并 post_count-1。结果：搜 vocaloid 搜不到该图，物化不变量被破坏。测试 test_update_post_replace_tags 只用无 implication 的标签，覆盖不到。

**最小修复**：计算 to_remove 前先把 target_ids 用 tags.closure_of(db, list(target_ids)) 展开：`to_remove = current_after_add - closure_of(db, target_ids)`。

**复核意见**：证据属实：post_edit.py:64 target_ids 只含直接标签，:69 tag_post 写入含后件的闭包，:78 to_remove=current_after_add-target_ids 会把后件行删除并 post_count-1（即使后件本来就在 post 上也会被删）。破坏 ADR-0001 物化不变量，搜索后件将漏掉该图。tests/test_post_edit.py:75-91 的替换测试用无 implication 的 a/b/c，无覆盖。最小修复：to_remove 改为 current_after_add - tags.closure_of(db, list(target_ids))。

## 4. [高] cascade-delete · backend/app/services/post_edit.py:111

**问题**：删除 post 时 post_tags 由 FK CASCADE 静默删除，Tag.post_count 不递减，计数永久漂移

**证据**：post_edit.py:111-112 `db.delete(post); db.commit()`，删除前未读取该 post 的 post_tags 也未触碰 Tag.post_count；spec database-guidelines.md 声明「post_count 恒等于该 tag 的 post_tags 行数」。

**触发场景**：post 带标签 a（a.post_count=1），DELETE /api/posts/{id} 后 post_tags 行被 CASCADE 删除但 a.post_count 仍为 1。反复导入-删除后 /tags 页与搜索排序（post_count desc）显示虚高计数，且 update_post 的 `t.post_count > 0` 保护掩盖不了正向漂移。测试 test_delete_post_cascade_and_files 只断言行删除，未查 post_count。

**最小修复**：delete_post 里删除行前先 `for (tid,) in db.execute(select(PostTag.tag_id).where(PostTag.post_id==post_id)): tag.post_count -= 1`（clamp 到 0），再 db.delete(post)。

**复核意见**：证据属实：models/tag.py:29 PostTag.post_id 是 ondelete=CASCADE，post_edit.py:111-112 直接 db.delete(post); db.commit()，全代码库删除路径无任何 post_count 递减。spec 声明 post_count 恒等于 post_tags 行数，漂移永久且正向（update_post 的 >0 保护只防负数）。test_delete_post_cascade_and_files 只断言行被删，未查 post_count。影响限于 /tags 计数与排序显示，但属数据完整性硬伤。最小修复：删除前查该 post 的 tag_id 并逐个 post_count-1。

## 5. [中] unauthenticated-media-mount · backend/app/main.py:30

**问题**：/media 静态目录整体挂载且不经任何认证，图片可被局域网内任何人直接拉取，也完全绕过 safe_mode 过滤

**证据**：main.py:28-30: `_media_dir = settings.media_path` … `app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")`，无 dependencies=[Depends(get_current_user)]（StaticFiles mount 本身也不支持依赖注入）；其余 API 均带 get_current_user/get_current_session（见 api/posts.py:46,67 等）

**触发场景**：局域网另一台设备不登录，直接 GET http://host:port/media/<相对路径>/xxx.jpg（路径可从缓存、日志或枚举得到）→ 200 返回原图，包括 rating 非 safe 的图；safe_mode 的后端注入只保护 /api/posts 列表，不保护文件本体

**最小修复**：把媒体改为经认证的路由：如 @router.get("/media/{path:path}") + Depends(get_current_user) 后 FileResponse（内部仍做 resolve+is_relative_to 校验），或在 mount 前加一层校验 gallery_session 的 ASGI 中间件；本地单机可接受现状，但局域网部署建议加

**复核意见**：证据属实：main.py:30 裸挂 StaticFiles，无任何认证包装，而所有 API 路由均带会话依赖；backend/tests/ 无 /media 访问控制测试。局域网未登录设备可直接拉取原图并绕过 safe_mode（safe_mode 只在 /api/posts 查询层注入 rating 过滤，不覆盖文件本体）。单用户局域网模型下属信息泄露而非远程可达，维持 medium。最小修复：改为带 get_current_session 依赖的 FileResponse 路由或用中间件校验会话 cookie。

## 6. [中] path-traversal · backend/app/services/media.py:170

**问题**：ingest 的 file_ext 未做白名单/字符校验就拼进写盘文件名，抓取链路的上游 JSON 可注入路径分隔符实现目录外写文件

**证据**：media.py:170 `(post_dir / f"{_ORIGINAL_NAME}.{file_ext}").write_bytes(data)`，且 174 行 `post.file_path = f"{rel_dir}/{_ORIGINAL_NAME}.{file_ext}"`。file_ext 来源之一是 danbooru.py:135 `file_ext = p.get("file_ext", "png") or "png"`（上游 JSON 原样透传，无任何校验）；本地导入路径 import_service.py:78 `ext = p.suffix.lower().lstrip(".")` 相对安全，但 scrape.py:86 `file_ext=sp.file_ext` 直通 ingest。

**触发场景**：上游 API 响应（被劫持的代理环境、未来接入的其它站点适配器、或 Danbooru 返回异常数据）中 file_ext 为 `png/../../../x.py` → Path 拼接后 write_bytes 写到 media 目录之外（Windows 下同样吃 `/`）；同时 file_path 带 `..` 入库。这是写侧穿越，StaticFiles 的读侧防护管不到。

**最小修复**：在 ingest 开头校验 `re.fullmatch(r"[a-z0-9]{1,5}", file_ext)`（或对齐 SUPPORTED_EXTS 白名单），不合法则抛 ValidationError；danbooru._parse_post 处同样收敛。

**复核意见**：证据属实：media.py:170/174 直接拼接 file_ext，danbooru.py:135 从上游 JSON 原样透传且全链路无白名单校验（grep 全后端仅此一条链）；Post.file_ext 的 String(8) 在 SQLite 不强制长度，且写盘发生在 commit 之前，DB 层无兜底；tests 仅用 png/gif，无恶意 ext 覆盖。含 ../ 的 ext 配合合法图片字节即可在 media 目录外写文件（写侧穿越，StaticFiles 读侧防护无效）。但触发前提是上游响应被控（HTTPS 直连 danbooru，需代理劫持或未来不可信适配器），非局域网对端可直接触发，故由 high 降为 medium。最小修复：ingest 或 ScrapedPost 处对 file_ext 做 ^[a-z0-9]{1,8}$ 白名单校验。

## 7. [中] apscheduler-worker-session-exception-handling · backend/app/services/import_service.py:89

**问题**：worker 循环里捕获 ingest 异常后不 rollback，脏 session 使后续所有文件的查询抛 PendingRollbackError，把整个任务拖成 failed

**证据**：import_service.py:89-90 `except Exception:\n            state.failed += 1`（无 db.rollback()）。media.ingest 在 db.flush()/db.commit()（media.py:165/178）抛 IntegrityError 后 session 进入 rollback-pending 态；下一轮循环 import_service.py:67 `db.execute(select(ScanHistory)...)` 会抛 PendingRollbackError，逸出 scan_directory 被 tasks.py:135 捕获为整任务 failed。scrape.py:92-94 的 `except Exception:` 同样无 rollback。

**触发场景**：两个并发任务（max_workers=3）撞到同一张图：任务 A 先 commit，任务 B 在 md5 unique 索引（models/post.py:34）上 IntegrityError → B 计 failed+1 但 session 未回滚 → B 后面成百上千个还没扫的文件全部因 PendingRollbackError 直接把任务打成 failed。

**最小修复**：在 import_service.py 与 scrape.py 的每个 `except DuplicateError/Exception` 分支里加 `db.rollback()`（或在 media.ingest 的 commit/flush 失败时自行 rollback 后 re-raise）。

**复核意见**：与 #1 同根因的另一表现：flush/commit 阶段 IntegrityError 后 session 进入 PendingRollback，下一轮 line 67 的 db.execute 抛 PendingRollbackError，逸出 scan_directory 被 tasks.py:135-139 兜底标整任务 failed。代码路径核实无误。但触发需要并发任务撞 md5 唯一索引的竞态窗口（select 检查在前，多数重复走 DuplicateError 分支），单用户下概率较低，降为 medium。

## 8. [中] rescan-rereads-duplicates · backend/app/services/import_service.py:87

**问题**：DuplicateError 分支不写 scan_history，重复文件在每次重扫时都被完整读入内存并重算 md5

**证据**：import_service.py:87-88: `except DuplicateError: state.duplicates += 1` 直接落到 line 99 `state.processed += 1`，跳过了 line 91-97 的 scan_history 记录（else 分支只在无异常时执行）；下次扫描 line 72 的 mtime 跳过对它永远不命中

**触发场景**：目录里有 5000 张图，其中 2000 张与库中已有图 md5 重复（如两份下载目录）：第一次扫描后重复文件不进 scan_history，之后每次增量重扫都要 read_bytes + md5 这 2000 个文件（可达数十 GB IO），增量扫描的意义被抵消

**最小修复**：把 scan_history 的写入从 else 分支提出来：DuplicateError 分支同样更新/插入 (path, mtime) 后 commit——文件没变化时它仍是重复，无需再读

**复核意见**：证据属实：line 87-88 DuplicateError 分支落空 else（line 91-97 的 scan_history 写入只在无异常时执行），重复文件每次重扫都要 read_bytes+md5。文件 mtime 未变、内容未变，记录 scan_history 完全安全。纯性能问题（增量扫描失效），单用户本地场景降为 low~medium；保留 medium 因大目录场景 IO 量可观。

## 9. [中] transaction-boundaries · backend/app/services/post_edit.py:69

**问题**：update_post 不是原子操作：tags.tag_post 在中途 commit，rating+新增标签先落库，之后删除阶段失败会留下「并集」中间态

**证据**：post_edit.py:43 先改 `post.rating`；:69 调 tags.tag_post，其内部 tags.py:237 `db.commit()` 把 rating 变更与新增行一起提交；删除阶段 :79-89 与最终 :92 commit 是第二个事务。

**触发场景**：PATCH {tags:[b,c], rating:'explicit'}（原有 a,b）：tag_post 提交后进程崩溃/删除阶段抛异常 → 数据库里 post 已是 explicit 且标签为 {a,b,c}（新旧并集），既非原状态也非目标状态，且无任何回滚路径；客户端收到 500 但半个写入已持久化。

**最小修复**：让 tag_post/create_implication 支持 flush-only 模式（去掉内部 commit，由最外层调用者统一 commit），或在 update_post 内用嵌套事务/单一 commit 收尾。

**复核意见**：证据属实：tags.py:237 tag_post 内部 db.commit() 会把 post_edit.py:43 的 rating 变更与新增闭包行一并提交，:79-92 的删除阶段是第二个事务；中途失败（如并发导入任务导致 SQLite busy、进程崩溃）留下新旧并集且 rating 已改的中间态，客户端却收到 500。单用户本地场景触发概率低但可达（APScheduler 导入任务与编辑并发是真实路径），维持 medium。最小修复：tag_post 增加 commit=False 参数（或改用 flush），由 update_post 统一提交。

## 10. [中] schema-field-consistency · backend/app/api/posts.py:36

**问题**：PostSummary/PostDetail 的 favorite 字段永远硬编码 False，但收藏 API 已实现并持久化，读端契约与写端脱节

**证据**：posts.py:36/80/136 均为 `favorite=False,  # favorites API lands later...`；但同文件 :104 `favorited = favorites.toggle_star(db, post_id)` 已真实写入 favorite_items（services/favorites.py:164-186）。前端 types.ts:35 `favorite: boolean`，post-card.tsx:22 `useState(post.favorite)` 以此初始化星标

**触发场景**：用户 POST /api/posts/5/favorite 得到 {favorited:true}，刷新页面后 GET /api/posts 返回该帖 favorite=false → 星标丢失显示，写读两端对同一字段给出矛盾答案

**最小修复**：在 search.list_posts / get_post 的响应组装处按 favorite_items 成员关系填充 favorite（对列表页可用一次 IN 查询批量取默认收藏夹成员集合），删除三处硬编码 False

**复核意见**：证据完全属实：posts.py:36/80/136 三处硬编码 favorite=False，而同文件 :104 toggle_star 已真实写入 favorite_items（test_favorites.py:165-189 证明写端持久化）。测试只断言 toggle 返回值，无任何测试覆盖读端 favorite 字段，故无兜底。写读契约矛盾、刷新后星标丢失是真实可复现缺陷。但单用户本地应用、纯 UX 数据错误，无安全影响，high 下调为 medium。

## 11. [中] unique-constraints-races · backend/app/services/favorites.py:72

**问题**：Favorite.name 无唯一约束，默认收藏夹按名字识别；重名后 get_or_create_default 的 scalar_one_or_none 抛 MultipleResultsFound，星标功能 500

**证据**：models/favorite.py:16 `name: Mapped[str] = mapped_column(String(128), nullable=False)` 无 unique；favorites.py:58-64 create_favorite 不查重直接插入；favorites.py:72-74 `db.execute(select(Favorite).where(Favorite.name == DEFAULT_FAVORITE_NAME)).scalar_one_or_none()`。

**触发场景**：用户先后 POST /api/favorites {name:'默认收藏'} 两次（或已星标过一次后再手建一个同名收藏夹）→ 表里两行同名；此后任何 POST /posts/{id}/favorite 在 scalar_one_or_none 处抛 MultipleResultsFound → 全局 500，星标功能不可用；两个『默认』还会导致 favorited 状态分裂。

**最小修复**：给 favorites.name 加 UNIQUE（Alembic batch 迁移），create_favorite 查重抛 ConflictError；get_or_create_default 改用 `.limit(1)` + `scalars().first()` 作为兜底。

**复核意见**：证据全部属实：迁移 f3d99311f0cf 中 favorites.name 无 UNIQUE（DB 层无兜底）；api/favorites.py:48 与 services/favorites.py:58-64 均不查重；favorites.py:72-74 用 scalar_one_or_none，同名两行必抛 MultipleResultsFound。场景可达：两次 POST /api/favorites {name:'默认收藏'}（或星标后再手建同名夹）即可复现，此后星标端点持续 500，且无 API 途径恢复。测试无覆盖（仅 test_post_edit.py:123 单次 toggle_star）。单用户属自伤型，但属正常操作路径导致的持久性功能瘫痪，维持 medium。最小修复：name 加唯一约束/索引 + create_favorite 查重抛 409，get_or_create_default 改用 .scalars().first() 兜底。

## 12. [中] cancel-requested-cooperative-cancel-window · backend/app/services/tasks.py:161

**问题**：scrape 任务的取消完全无效：整个抓取批次跑完之前从不检查 cancel_requested，进度也全程 0/0

**证据**：tasks.py:161 `result = scrape_svc.scrape_to_db(db, scraper, query, limit=limit)`，随后 :172 才 `state.status = "cancelled" if state.cancel_requested else "completed"`。而 scrape.py:57-107 的 `for sp in posts:` 循环里没有任何 is_cancelled 检查，也不更新 state.processed/total（tasks.py:162 只在批次结束后一次性写入）。对比 _run_scan 把 `_is_cancelled` 传给 scan_directory（tasks.py:134），scrape 路径没有等价物。

**触发场景**：用户提交 limit=100 的 scrape → 每个 post 至少 1 秒限速 + 30 秒超时下载（danbooru.py:54, base.py:102），任务要跑数分钟；用户 POST /api/tasks/{id}/cancel 得到 cancelled=true，但轮询进度一直是 running 且 processed=0/total=0，直到全部 100 个 post 抓完才被标成 cancelled（实际全做完了）。

**最小修复**：给 scrape_to_db 增加 `is_cancelled: Callable[[str], bool]` 与 state 参数（与 scan_directory 同型），循环每个 post 开头 `if is_cancelled(task_id): return result`，并逐 post 递增 state.processed（total 在 search 返回后设为 len(posts)）。

**复核意见**：证据属实：tasks.py:161 整批调用 scrape_to_db，scrape.py:57 的 for 循环无任何 is_cancelled 检查，取消标志只在 :172 批次结束后才被看一次；对比 _run_scan(:134) 把 _is_cancelled 传入。tests/test_import_tasks.py 的 test_task_cancel 只验证了 scan 路径（deferred scheduler + cancel_src 目录），scrape 取消无测试覆盖。取消功能对 scrape 完全失效成立。但单用户本地场景下这是 UX/功能缺陷而非安全硬伤，且限速下载导致的耗时是最坏场景——降为 medium。

## 13. [中] task-progress-granularity · backend/app/services/tasks.py:162

**问题**：scrape 任务的进度只在整批结束后一次性写入，且 scrape 循环从不轮询取消标志——进度端点全程显示 0/0，取消对 scrape 无效

**证据**：tasks.py:161-164: `result = scrape_svc.scrape_to_db(...)` 返回后才 `state.processed = state.total = ...`；scrape.py:57 `for sp in posts:` 循环体内既不更新 state 也不调用 is_cancelled（对比 scan 路径 import_service.py:56 每文件轮询）

**触发场景**：用户发起 limit=100 的抓取，前端轮询 /import 进度端点：整个下载期间 processed/total 恒为 0/0 无法区分卡死与运行中；点取消后 cancel_requested 置位但 worker 不看它，仍下载完全部 100 张才结束

**最小修复**：给 scrape_to_db 增加与 scan_directory 相同的 `state: TaskState, is_cancelled` 参数：search 后先 `state.total = len(posts)`，循环每帖 `state.processed += 1` 并 `if is_cancelled(task_id): return result`

**复核意见**：证据属实且与 index 0 基本同根：tasks.py:161-164 进度只在整批返回后写入，scrape.py:57 循环内既不更新 state 也不轮询取消（对比 import_service.py:53-56 scan 路径每文件更新 total/processed 并轮询）。前端轮询期间恒 0/0、无法区分卡死与运行中，场景真实可达。功能性缺陷，medium 维持。建议与 index 0 合并修复：给 scrape_to_db 增加 progress/is_cancelled 回调。

## 14. [中] sqlite-wal-busy-timeout-long-transaction · backend/app/db.py:33

**问题**：未配置 busy_timeout，且 ingest 在持有写事务期间做磁盘文件 IO，多 worker 并发时易触发 database is locked

**证据**：db.py:33-35 只设置了 journal_mode=WAL / foreign_keys / synchronous，没有 `PRAGMA busy_timeout`，create_engine（db.py:17-23）也未传 connect_args timeout（sqlite3 默认仅 5 秒）。而 media.py:165-178 在 `db.flush()`（开启写事务）之后才 `write_bytes(data)` 写原图+两张缩略图再 `db.commit()`——写事务横跨最大 200MB（import_service.py:33）的文件落盘。

**触发场景**：scheduler max_workers=3（tasks.py:60）允许 scan 与 scrape 并发：worker A ingest 一张大图，写事务持锁超过 5 秒（慢盘/大文件），worker B 或前端触发的写请求（收藏、tag 编辑）等锁超时 → sqlite3.OperationalError: database is locked，被 scan 循环记成 failed 或让请求 500。

**最小修复**：最小改法：在 _set_sqlite_pragma 中加 `cur.execute("PRAGMA busy_timeout=30000")`（或 connect_args={"timeout": 30}）；更进一步可把三个 write_bytes 移到 flush 之前（先算 id 需要重构，故 busy_timeout 是最小修复）。

**复核意见**：证据属实：db.py:28-36 仅设 WAL/foreign_keys/synchronous，无 busy_timeout；db.py:17-23 connect_args 无 timeout（默认 5s）。media.py:165-178 确实在 flush() 开写事务后才 write_bytes 原图+两张缩略图再 commit，写锁横跨最大 200MB 文件落盘。tasks.py:60 max_workers=3 允许 scan/scrape 并发，前端收藏/tag 编辑也走独立会话写库，场景可达。测试 test_concurrent_tasks 用 sync_scheduler 同步执行，未覆盖真实并发锁竞争。单用户本地场景下属可靠性问题而非安全问题，维持 medium；最小修复：pragma 里加 busy_timeout（或 connect_args timeout），并把文件落盘挪到写事务之外。

## 15. [中] pyproject-deps-mismatch · backend/pyproject.toml:7

**问题**：httpx 在运行时代码中被 import，但只声明在 dev 可选依赖里，生产安装缺依赖

**证据**：backend/app/scrapers/base.py:19 与 backend/app/scrapers/danbooru.py:18 均为顶层 `import httpx`；而 pyproject.toml 主 dependencies（fastapi/uvicorn/sqlalchemy/alembic/pydantic-settings/bcrypt/python-multipart/pillow/imagehash/apscheduler）不含 httpx，httpx>=0.26 只出现在 [project.optional-dependencies].dev 中

**触发场景**：按 `pip install .`（不带 [dev]）部署后，用户调用 POST /api/import/scrape → app/api/import_.py:151 延迟 `from app.services import scrape as scrape_svc` → scrape.py:28 import app.scrapers.base → `import httpx` 抛 ModuleNotFoundError，任务直接崩溃（500）。63 例测试全绿是因为 CI 装了 dev extras，掩盖了该漂移

**最小修复**：把 "httpx>=0.26" 从 [project.optional-dependencies].dev 移入 [project].dependencies（dev 中可保留也可删除）

**复核意见**：证据属实：backend/app/scrapers/base.py:19 和 danbooru.py:18 顶层 `import httpx`，而 pyproject.toml 主 dependencies（第6-17行）不含 httpx，仅在 [project.optional-dependencies].dev（第22行）声明；fastapi/uvicorn[standard] 均不会传递性引入 httpx。场景可达：`pip install .` 后 POST /api/import/scrape → services/tasks.py:150-151 惰性导入 DanbooruScraper/scrape_svc → ModuleNotFoundError。tests/ 依赖 httpx（TestClient），CI 全绿确实掩盖了漂移。但两处细节需修正：(1) 惰性导入发生在后台 worker `_run_scrape`（tasks.py:146），异常被 tasks.py:165 `except Exception` 捕获，任务标记 failed 并把错误写入 state.error——不是 500 崩溃，API 本身返回 201，失败可通过任务状态查询到，属优雅降级；(2) 该功能本就受 README 已知约束（Danbooru 被 Cloudflare 403 拦截），生产环境即使有 httpx 也大概率失败。因此从 high 降为 medium：真实的打包依赖漂移，最小修复是把 `httpx>=0.26` 移入主 dependencies（backend/pyproject.toml:6-17），但在单用户本地部署（通常按开发方式装依赖）且失败可观测的前提下不构成硬伤。

## 16. [低] error-envelope-coverage · backend/app/main.py:33

**问题**：Pydantic/FastAPI 的 422 校验错误未接入统一错误信封，返回 {"detail":[...]}，违反 error-handling.md「Every non-2xx response uses this shape」

**证据**：main.py 只注册了 `app.add_exception_handler(AppError, app_error_handler)` 和 `(Exception, unhandled_exception_handler)`，没有 RequestValidationError 处理器；前端 lib/api.ts:37-41 只认 `body?.error` 字段，否则回退到 `请求失败 (422)`

**触发场景**：POST /api/auth/setup 密码只有 4 位（<min_length 8）→ FastAPI 默认返回 422 {"detail":[...]} → 前端 ApiError 落入兜底分支，用户只看到「请求失败 (422)」而非可读的校验消息

**最小修复**：在 main.py 加 `app.add_exception_handler(RequestValidationError, handler)`，把校验错误转成 {"error":{"code":"validation_error","message":<拼接的可读消息>}}，状态码保持 422

**复核意见**：证据属实：main.py:33-34 只注册 AppError 与 Exception 处理器，无 RequestValidationError 处理器，422 返回 FastAPI 默认 {detail:[...]}；error-handling.md:37 明确「Every non-2xx response uses this shape」且未豁免校验错误；frontend/lib/api.ts:38-41 确实只解析 body.error，422 时落入「请求失败 (422)」兜底。但影响仅为错误提示可读性（UX），无安全/数据风险，降为 low。修复：add_exception_handler(RequestValidationError, ...) 转成统一信封。

## 17. [低] media-cache-control · backend/app/main.py:30

**问题**：/media 用裸 StaticFiles 挂载，不发 Cache-Control——画廊每次渲染都对每张缩略图发条件请求回源后端

**证据**：main.py:30: `app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")`，无任何响应头定制。Starlette StaticFiles 只发 ETag/Last-Modified（流式与 Range 已内置），无 Cache-Control 时浏览器每次导航都要 304 revalidate

**触发场景**：画廊一页 40 张缩略图，用户来回翻页/进出详情：每张图每次都打一条 GET 到 FastAPI（304），几百条请求穿过 Next.js rewrite 代理压到后端；而 posts/{id}/ 下的文件内容不可变（同 id 永不重写），本可长缓存

**最小修复**：子类化 StaticFiles 覆写 file_response（或加一层 middleware 按路径前缀 /media 注入）添加 `Cache-Control: public, max-age=31536000, immutable`；删除图片时 id 不复用即安全

**复核意见**：证据属实：main.py:30 无响应头定制，Starlette StaticFiles 默认不发 Cache-Control，浏览器每次导航对缩略图逐张 304 revalidate。但单用户本地/局域网部署下 304 延迟可忽略，且内容不变时不重传字节，纯性能优化项而非缺陷，降为 low。修复：子类化 StaticFiles 覆写 file_response 加 Cache-Control: public, max-age=31536000, immutable（文件按 id 落盘不重写，可安全长缓存）。

## 18. [低] setup-endpoint-race · backend/app/api/auth.py:48

**问题**：/setup 的 has_user 检查与 create_user 非原子，并发首次创建时两个不同用户名的请求可同时通过检查，产生两个用户，破坏单用户假设

**证据**：api/auth.py:48-50: `if auth.has_user(db): raise ConflictError(...)` 后才 `auth.create_user(...)`；services/auth.py:100-106 直接 INSERT+commit；models/user.py:18 只有 username 唯一约束，挡不住不同用户名的并发插入

**触发场景**：首次部署时两个并发 POST /auth/setup（username=a 与 username=b）都在对方 commit 前执行 has_user → 都为 False → users 表出现两行，二者都能登录；后续代码/运维按“单用户”假设操作会出错

**最小修复**：让 create_user 固定 id=1（User(id=1, ...)），第二个并发插入触发主键 IntegrityError，捕获后转 ConflictError；一行改动即可闭合竞态

**复核意见**：证据属实：api/auth.py:48-50 check 与 create 分属两次事务，services/auth.py:100-106 中 create_user 前还有 ~100ms 的 bcrypt 哈希，TOCTOU 窗口真实存在；models/user.py:18 仅 username 唯一，不同用户名并发插入无 DB 兜底。tests/test_auth.py:40 只测顺序第二次 409，无并发覆盖。但首次部署窗口极短且需本人并发自打，单用户本地场景维持 low。

## 19. [低] cookie-lifetime-mismatch · backend/app/api/auth.py:30

**问题**：set_cookie 未设 max_age/expires，cookie 是浏览器会话级，而服务端 session 有效期 30 天，二者不一致；浏览器关闭即丢登录态但服务端 token 仍有效 30 天

**证据**：api/auth.py:30-36 _COOKIE_KWARGS 只有 key/httponly/samesite/secure/path，无 max_age；services/auth.py:39 `expires_at = now + timedelta(days=settings.session_expire_days)`（config.py:31 默认 30 天）

**触发场景**：用户关浏览器 → cookie 消失需重新登录（体验问题），同时服务端残留可用 30 天的 token（配合上一条堆积问题）；若期望持久登录则功能未达成

**最小修复**：在 _COOKIE_KWARGS 增加 `"max_age": settings.session_expire_days * 86400`，与服务端过期对齐

**复核意见**：证据属实：api/auth.py:30-36 _COOKIE_KWARGS 无 max_age/expires，cookie 为会话级；services/auth.py:39 服务端 session 30 天。关浏览器即失登录态而服务端 token 残留，行为与 30 天配置意图不一致。体验/清理问题，非安全硬伤，low。

## 20. [低] status-code-semantics · backend/app/api/auth.py:45

**问题**：POST /api/auth/setup 创建用户资源却显式返回 200，而项目内其他创建端点（tags/favorites/import）统一用 201

**证据**：auth.py:45 `@router.post("/setup", response_model=UserResponse, status_code=status.HTTP_200_OK)`；对比 api/tags.py `status_code=status.HTTP_201_CREATED`、api/favorites.py 创建、api/import_.py submit_scan/submit_scrape 均为 201

**触发场景**：首次运行调用 /setup 成功创建 admin 用户，返回 200；同项目内 201 语义不一致，客户端或未来自动化按 201 判断创建成功会误判

**最小修复**：把 status_code 改为 status.HTTP_201_CREATED（前端 lib/api.ts 用 res.ok 判断，200/201 均兼容，改动零风险）

**复核意见**：证据属实：api/auth.py:45 显式 status_code=HTTP_200_OK，而 tags/favorites/import 的创建端点均为 201（tests 中多处 assert 201 佐证项目惯例）。纯语义一致性问题，low。

## 21. [低] spec-thin-routes · backend/app/api/auth.py:93

**问题**：update_settings 路由内直接改 ORM 字段并 commit（业务持久化逻辑写在 api/ 层），违反 directory-structure/quality 的「Routes stay thin，No business logic in route handlers」

**证据**：api/auth.py:93-96 `session.safe_mode = payload.safe_mode; db.add(session); db.commit(); db.refresh(session)` 直接在路由函数体内。

**触发场景**：后续任何非 HTTP 调用方（如任务或测试）想切换 safe_mode 无服务函数可复用；且该文件是规范点名的「Clean layered route」示例，本处破坏了分层一致性。

**最小修复**：在 services/auth.py 增加 `set_safe_mode(db, session_row, value) -> SessionRow`，路由只调用它。

**复核意见**：证据属实：api/auth.py:93-96 在路由内直接改 ORM 字段并 commit；spec directory-structure.md:45/62 明文'Routes stay thin'且点名 auth.py 为分层示范，quality-guidelines.md:19 禁止路由内业务逻辑。虽仅一个字段的持久化，仍无可复用服务函数（services/auth.py 无对应 set_safe_mode），违规成立但影响轻微，low。

## 22. [低] expired-session-cleanup · backend/app/services/auth.py:65

**问题**：过期会话行只在读取时被判定为无效，从不物理删除；除显式 /logout 外没有任何清理机制，sessions 表随时间只增不减

**证据**：services/auth.py:65 `if row.expires_at <= datetime.utcnow(): return None` 仅返回 None 不删行；全仓 grep 无针对 sessions 的定期清理任务（app/services/tasks.py 的 APScheduler 只调度 import 任务）；delete_session 仅在 api/auth.py:71 logout 时调用

**触发场景**：每次登录（api/auth.py:62）都新增一行、30 天过期后残留；长期运行（尤其多设备/常清 cookie 的浏览器）导致 sessions 表堆积失效 token 明文行，DB 泄露时暴露历史 token 痕迹

**最小修复**：在 validate_session/get_session_row 命中过期行时顺手 db.delete(row)+commit，或在 APScheduler 加每日 `DELETE FROM sessions WHERE expires_at <= now` 清理作业

**复核意见**：证据属实：services/auth.py:65 与 :79 对过期行仅返回 None 不删除；delete_session 只在 api/auth.py:71 logout 调用；services/tasks.py 的 APScheduler 只调度 import 任务，全仓无 sessions 清理逻辑；tests/test_auth.py:92 仅验证过期会话被拒绝（AC12），未覆盖清理。场景可达：每次 /login（api/auth.py:62）与 /setup（:51）都插入新行，过期后永久残留。但单用户本地/局域网部署下增长极慢（token 行 <100 字节，靠人工登录触发），且过期 token 无法再用于认证，仅是 DB 卫生/泄露痕迹问题——维持 low。最小修复：启动时或 APScheduler 定期执行 DELETE FROM sessions WHERE expires_at <= now。

## 23. [低] bcrypt-72-byte-truncation · backend/app/services/auth.py:25

**问题**：bcrypt 静默截断 72 字节以后的密码内容，超长密码的尾部不参与校验；算法与 cost=12 本身合格，仅此边界未处理

**证据**：services/auth.py:23-29 hash_password/verify_password 直接把 password.encode("utf-8") 交给 bcrypt.hashpw/checkpw，未做长度校验或预哈希；SetupRequest/LoginRequest（schemas/auth.py）也未限制密码字节长度

**触发场景**：用户设 80 字符密码，之后凡前 72 字节相同的任意输入都能登录（例如尾部改动的变体），与用户预期不符

**最小修复**：在 SetupRequest 的 password 字段加 max_length（如 64），或 hash 前先 sha256 预哈希再 bcrypt

**复核意见**：证据属实：services/auth.py:25/29 直接把 password.encode('utf-8') 交给 bcrypt，无预哈希或字节长度校验；schemas/auth.py:9 允许 max_length=128 字符（UTF-8 下最多 512 字节），远超 72 字节边界，场景可达。requirements.txt 仅约束 bcrypt>=4.1：4.x 静默截断（前 72 字节相同即可通过校验，与发现描述一致）；若解析到 5.x 则 hashpw/checkpw 对 >72 字节直接抛 ValueError，/setup 与 /login 变成未处理 500——两种版本都有边界缺陷，发现成立。单用户自设密码、本地部署，实际被利用价值极低，维持 low。最小修复：schema 校验密码 UTF-8 字节数 ≤72，或 hash 前先 SHA-256 预哈希。

## 24. [低] scraper-ssrf · backend/app/scrapers/base.py:102

**问题**：Scraper.download 对 image_url 无 scheme/host 校验，上游 JSON 可指挥后端向任意地址（含内网）发请求并把响应存为图片

**证据**：base.py:102 `resp = httpx.get(image_url, timeout=30.0, follow_redirects=True)`；image_url 来自 danbooru.py:134 `p.get("file_url") or p.get("large_file_url") or p.get("preview_file_url", "")`，未检查协议或域名，follow_redirects=True 还接受任意跳转。

**触发场景**：上游响应（或中间人/恶意镜像代理）把 file_url 写成 `http://192.168.1.1/admin` 或 `http://169.254.169.254/...` → 后端主动请求内网地址，响应字节被 ingest 落库并经 /media 对外提供，形成内网信息带出通道。

**最小修复**：download 前校验 `urlparse(image_url)`：scheme 必须是 https、host 必须匹配站点白名单（如 endswith('.donmai.us')），重定向后也校验（用 client 手动跟或 follow_redirects=False）。

**复核意见**：证据属实：base.py:102 无 scheme/host 校验且 follow_redirects=True，image_url 直通 danbooru.py:134 上游 JSON，scrape.py:71 无兜底，测试无覆盖。但触发需上游被攻陷或 MITM（Danbooru API 走 HTTPS），且抓取仅 admin 发起，单用户局域网下利用链较长，降为 low。

## 25. [低] download-size-limit · backend/app/scrapers/base.py:106

**问题**：抓取下载无大小上限，resp.content 一次性读入内存；本地导入的 200MB 上限（import_service.MAX_FILE_BYTES）对抓取链路不生效

**证据**：base.py:106 `return resp.content`（无 Content-Length 检查、无流式截断）；对比 import_service.py:33 `MAX_FILE_BYTES = 200 * 1024 * 1024` 只用在 scan_directory:51 的本地文件过滤。

**触发场景**：上游 file_url 指向一个几 GB 的响应（恶意或异常）→ httpx 全量读入内存，随后 media.ingest 再复制一份 bytes 做 md5/Pillow 解码，单请求即可把后端进程内存打爆（DoS）。

**最小修复**：改为 `with httpx.stream(...)` 分块读取，累计超过 MAX_FILE_BYTES（复用同一常量）即中断并抛 ScraperError。

**复核意见**：证据属实：base.py:106 resp.content 全量读入内存，无大小上限；import_service 的 200MB 上限仅作用于本地扫描路径，测试用假 scraper 未覆盖。但需上游返回超大响应，且 DoS 只影响操作者自己的进程，单用户场景影响有限，降为 low。修复廉价：httpx.stream + 字节上限。

## 26. [低] scan-filesystem-race-stat · backend/app/services/import_service.py:51

**问题**：构建文件清单时 p.stat() 无异常保护，扫描期间文件被删除/占用会让整个任务直接 failed

**证据**：import_service.py:49-52 `files = sorted(p for p in _walk_files(root) if p.suffix.lower() in SUPPORTED_EXTS and p.stat().st_size <= MAX_FILE_BYTES)` —— stat 在生成器表达式里裸调用；循环体内 getmtime 有 try/except OSError（:61-65），清单阶段没有。

**触发场景**：用户对正在被其他程序写入/删除的目录发起 scan（后台任务与外部进程并发操作同一目录）：os.walk 列到的某文件在 stat 前被删 → FileNotFoundError 逸出 → tasks.py:135 把整个任务标 failed，一个文件都没导入。

**最小修复**：把过滤抽成小函数，对 p.stat() 包 try/except OSError 返回 False 跳过该文件。

**复核意见**：证据属实：import_service.py:49-52 生成器内 p.stat() 裸调用，而循环体内 getmtime 有 try/except OSError（:61-65）——同一文件对不一致的防护说明这是疏漏而非取舍。异常会传播到 tasks.py:135 使整任务 failed。单用户局域网下 low 恰当。

## 27. [低] scan-walk-fragility-and-memory · backend/app/services/import_service.py:51

**问题**：扫描前置阶段在列表推导内对每个文件 p.stat()，文件在遍历期间被删除/无权限会抛 OSError 使整个任务直接 failed；且整棵目录树的路径列表一次性驻留内存

**证据**：import_service.py:49-52: `files = sorted(p for p in _walk_files(root) if p.suffix.lower() in SUPPORTED_EXTS and p.stat().st_size <= MAX_FILE_BYTES)` —— stat 无 try 包裹，异常会传播到 tasks.py:135 的兜底 except，任务标 failed、零进度

**触发场景**：扫描一个正被下载器写入的大目录：某临时文件在 walk 后、stat 前被改名删除 → FileNotFoundError → 整个扫描任务失败，已排队的几万张图一张没导；十万级文件时 sorted 列表也占数十 MB 且 total 出来前进度恒 0

**最小修复**：把 stat 移进主循环的 per-file try（或推导内用 try 包裹的辅助函数返回 None 过滤），单文件异常计 failed 不中断

**复核意见**：与 #3 重复（stat 裸调用同一问题），附带的内存论点（sorted 全量驻留、total 出来前进度恒 0）属实但属设计取舍（需要 total 才能报进度）。核心缺陷同 #3，建议合并。

## 28. [低] spec-error-handling-silent-swallow · backend/app/services/import_service.py:89

**问题**：扫描/抓取的逐文件 `except Exception:` 只做计数不记日志，违反 error-handling「services must not swallow silently — either handle and log, or let it propagate」

**证据**：import_service.py:89 `except Exception:  state.failed += 1`（吞掉具体异常，failed 只是个数字）；services/scrape.py:72、:92、:100-104 同样 bare `except Exception:` 仅计数。

**触发场景**：本地扫描 500 张图报 failed=37，用户/开发者无从得知是哪 37 个文件、因为解码失败还是磁盘错误——只能逐个二分重试。

**最小修复**：每个 except 分支加 `logger.warning("ingest failed path=%s err=%s", path_str, exc)`（scrape 侧记 source_id），计数逻辑不变。

**复核意见**：spec 明文命中：.trellis/spec/backend/error-handling.md:57「services must not except: pass — either handle and log, or let it propagate」。import_service.py:89-90 及 scrape.py 的 except Exception 只计数不记日志，确实违反项目自身规范；failed=N 无法定位是哪个文件、什么错。low 恰当。

## 29. [低] schema-length-bounds · backend/app/schemas/task.py:8

**问题**：ScanRequest.path 与 ScrapeRequest.query 无 max_length，超长字符串会被原样入调度参数并拼进上游请求 URL

**证据**：task.py:8 `path: str = Field(min_length=1)`、task.py:12 `query: str = Field(min_length=1)`（均无 max_length）；query 经 tasks.submit_scrape → danbooru.py:90 `self._get("/posts.json", {"tags": query, ...})` 直接作为查询参数。对比 auth/tag schema 均有 max_length（如 tag name ≤200）。

**触发场景**：提交 1MB 的 query/path 字符串 → 任务照常入队，扫描侧对超长非法路径做无谓 walk，抓取侧生成超长 URL 请求上游（431/URI too long 计入 failed），浪费 worker 且日志/内存被撑大；与项目其余 schema 的边界约定不一致。

**最小修复**：ScanRequest.path 加 max_length=1024，ScrapeRequest.query 加 max_length=512（与其余 schema 的显式上界约定对齐）。

**复核意见**：证据属实：task.py:8/12 确无 max_length，与 auth/tag/favorite schema 均设上限的项目约定不一致；字符串经 tasks.py:86/93 原样入调度参数，scrape query 拼进上游请求 URL，链路上无任何长度兜底（不入库，DB 约束不适用），tests 也无覆盖。但两端点均挂 get_current_user 认证，只有唯一 admin 能触发，且非法超长 path 会在 _walk_files 快速失败，实际影响仅为单次任务失败与日志膨胀。维持 low：一致性/卫生问题，最小修复是给两字段加 max_length（如 path≤1024、query≤512）。

## 30. [低] safe-mode-coverage · backend/app/api/posts.py:64

**问题**：safe_mode 只在列表注入，详情 GET /posts/{id} 与 /posts/{id}/next 完全不过滤 rating，直接输 id 即可绕过

**证据**：api/posts.py:64-71 get_post 用 get_current_user 而非 get_current_session，调用 search.get_post（search.py:69 docstring 自述 "any rating/duplicate state"）；post_edit.py:123-139 next_post 明确 "Not filtered by tags/safe_mode"，返回的 prev/next 会落到 explicit 图。

**触发场景**：会话 safe_mode=True：列表看不到 explicit 图，但直接访问 /api/posts/123（explicit）返回完整详情含 file_path，前端 /media 同源代理即可看原图；或在 safe 图详情页按方向键，next 返回 explicit 图 id 并跳转。safe_mode 的『后端权威注入』承诺在详情/导航读路径失效。

**最小修复**：get_post/next 路由改依赖 get_current_session；search.get_post 加 safe_mode 参数（safe_mode 且 rating!='safe' 时 raise NotFoundError），next_post 的两个查询在 safe_mode 时补 `Post.rating=='safe'` 条件。

**复核意见**：证据属实：GET /posts/{id} 与 /next 确实不注入 rating 过滤（posts.py:64-91,108-116；search.py get_post『any rating』）。但 next_post 的 docstring 明确写了『Not filtered by tags/safe_mode』——是有意的设计取舍而非遗漏；且单用户应用里 safe_mode 是同一用户对自己的偏好开关（他本可 PATCH /me/settings 直接关掉），不构成认证/权限绕过。与『后端权威注入』的架构承诺存在一致性缺口（详情页方向键会导航到 explicit 图），确认为低危一致性问题而非安全问题。

## 31. [低] spec-quality-stale-docstring · backend/app/api/posts.py:36

**问题**：favorite 字段在 list/detail/patch 三处硬编码 False，注释「favorites API lands later」已过时——favorites 已实装（同文件就有 toggle_favorite 路由），违反「favorited state 由 favorite_items membership 派生」及「注释必须匹配最新设计」两条规范

**证据**：api/posts.py:36 `favorite=False,  # favorites API lands later...`，:80 与 :136 同样 `favorite=False`；而 :104 起 `POST /posts/{id}/favorite` 已调用 favorites.toggle_star。

**触发场景**：用户收藏某图后刷新画廊或打开详情页，API 仍返回 favorite=false，星标状态与 favorite_items 实际 membership 不一致，前端无法正确渲染已收藏状态。

**最小修复**：list_posts/get_post/update_post 里用一次 `select(FavoriteItem.post_id).where(post_id in ...)` 派生 membership 填充 favorite，并删除过时注释。

**复核意见**：证据属实：posts.py:36 注释『favorites API lands later』已过时（同文件 :94-105 favorites 路由已实装），违反注释与设计同步的规范。但这与 index 1 是同一根因的规范/文档视角重述，修复时一并解决（读端派生 membership + 删注释），单独价值仅为文档卫生，定为 low。

## 32. [低] unique-constraints-races · backend/app/services/tags.py:214

**问题**：tag_post/update_post 的标签 get-or-create 是先查后插，后台导入线程与前台 PATCH 并发创建同名标签时撞唯一约束变成 500/failed

**证据**：tags.py:214-218 `tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none(); if tag is None: tag = Tag(...); db.flush()`；post_edit.py:58-62 同一模式。Tag.name 有 unique=True（models/tag.py:16），冲突时 flush 抛 IntegrityError。

**触发场景**：本地导入任务在 APScheduler 工作线程用独立 session 跑（spec 明确后台任务独立 session），同时用户在前台给图片打同名新标签：两个 session 都判定 tag 不存在并插入，后提交方 IntegrityError → PATCH 返回 500 或导入该文件计入 failed，且脏 session 若未回滚会连带污染后续操作。

**最小修复**：flush 处捕获 IntegrityError 后 rollback-重查一次（get-or-create 重试一轮）；单用户场景保持简单即可，不必上 upsert。

**复核意见**：代码证据属实（tags.py:214-218、post_edit.py:58-62 先查后插，Tag.name unique，全仓无 IntegrityError 处理/rollback），且 scrape.py:100-104 捕获异常后不回滚会污染后续循环。但审计场景有误：本地导入不打标签（import_service.py:9 明确 'Local imports carry no tags'），唯一后台标签写入方是 scrape 任务，而真实 Danbooru 抓取被 Cloudflare 403 挡住；单用户下仅剩双标签页/双击并发 PATCH 这类极窄窗口。成立但仅理论层面，维持 low。最小修复：get-or-create 处 try flush / except IntegrityError → rollback 重查。

## 33. [低] n-plus-one · backend/app/services/tags.py:300

**问题**：create_implication 回填对每个受影响 post 单独 SELECT 其 post_tags，再逐 tag db.get(Tag)——antecedent 帖子多时一个事务内数千条查询

**证据**：tags.py:292-312: 先 `.all()` 取全部 affected_post_ids，随后 `for pid in affected_post_ids:` 内每轮执行 `select(PostTag.tag_id).where(PostTag.post_id == pid)`，且每插一行 PostTag 就 `db.get(Tag, tid)` 并 +1

**触发场景**：对已有 5000 帖的热门标签（如 'genshin_impact'）建 implication：循环发 5000 次 SELECT + 每新行一次 Tag 取回，单事务持锁数秒~数十秒，期间 WAL 写阻塞其他写入（导入任务的 per-file commit 会等锁）

**最小修复**：一次 `select(PostTag.post_id, PostTag.tag_id).where(PostTag.post_id.in_(affected_post_ids))` 建 dict[pid→set]；Tag 对象按 new_closure 预取一次复用；post_count 用聚合后的 UPDATE 一次加总

**复核意见**：证据属实：tags.py:300-312 对每个受影响 post 单独 SELECT post_tags，插行时 db.get(Tag)。但影响被高估：两列均有索引，SQLite 进程内单查询微秒级，db.get 命中 identity map（每个 tag 只真查一次），5000 帖约数千次微秒级查询，实际锁持有远低于'数十秒'；且建 implication 是低频一次性管理操作，单用户场景无实质写阻塞。属真实 N+1 低优先级优化：可一次 IN 查询取全部 (post_id, tag_id) 组合并预取 closure 内的 Tag。维持 low。

## 34. [低] duplicate-task-submission-dedup · backend/app/services/tasks.py:83

**问题**：同一路径/同一 query 可重复提交并发任务，无任何去重，两个 worker 同时扫同一目录互相制造 IntegrityError

**证据**：tasks.py:83-94 submit_scan/submit_scrape 直接 `_register(kind)` + `add_job(...)`，_tasks 里没有按 (kind, path/query) 查重的逻辑；api/import_.py:41-60 也原样透传。

**触发场景**：前端按钮双击或用户重复提交同一目录的 scan → 两个 worker 并发遍历同一批文件，双方都在 md5 检查（media.py:126）看到不存在然后都 insert，一方撞 unique 索引 IntegrityError（被计成 failed 而非 duplicate），再叠加脏 session 问题（见另一条）使整个任务失败。

**最小修复**：submit_scan/submit_scrape 提交前在 _tasks_lock 内检查是否已存在同 kind+参数且 status in (pending, running) 的任务，存在则直接返回旧 task_id（需在 TaskState 上存 path/query）。

**复核意见**：证据属实：tasks.py:83-94 与 api/import_.py:41-60 均无按 (kind, path/query) 去重；max_workers=3 允许并发。场景可达但需双击竞态且两 worker 恰好同时处理同一文件才撞 md5 唯一索引；多数情况下后到者会命中 md5/source dedup 被计为 duplicate（media.py:126, scrape.py:59）。副作用是 IntegrityError 后 import_service.py:89 的 except 不 rollback，脏 session 会把余下文件全计 failed——真实但触发概率低、无数据损坏（DB 约束兜底）。单用户本地应用降为 low。

## 35. [低] scheduler-shutdown-inflight-tasks · backend/app/services/tasks.py:71

**问题**：shutdown 时只 shutdown(wait=False)，不给在途任务广播 cancel_requested；非 daemon 线程会把进程退出卡到长任务自然结束

**证据**：tasks.py:67-72 `_scheduler.shutdown(wait=False)` 后置 None，没有遍历 _tasks 设置 cancel_requested。APScheduler 的 ThreadPoolExecutor 线程非 daemon，Python 3.9+ 在解释器退出时会 join 这些线程。

**触发场景**：一个 limit=100 的 scrape 在跑（每 post ≥1s 限速 + 最多 4 次重试各 30s 超时）→ 用户 Ctrl+C 停 uvicorn → shutdown 钩子返回但进程要等这条抓取线程跑完才真正退出，可能挂住数分钟，期间看似进程僵死。

**最小修复**：shutdown_scheduler 里先 `with _tasks_lock: [setattr(s, 'cancel_requested', True) for s in _tasks.values()]` 再 shutdown（并配合 scrape 循环的取消检查，见另一条）。

**复核意见**：证据属实：tasks.py:67-72 shutdown(wait=False) 不广播 cancel_requested；APScheduler 的 ThreadPoolExecutor 基于 concurrent.futures，其 worker 线程在解释器退出时被 _register_atexit join，叠加 scrape 无取消轮询（见 index 0），Ctrl+C 后进程可能挂数分钟。场景可达，但只影响关停体验，无数据风险（每文件 db.commit），low 恰当。

## 36. [低] spec-error-handling · backend/app/services/tasks.py:137

**问题**：任务失败时把 str(exc) 原样放进 API 响应，违反 quality-guidelines 明令禁止的「Returning str(exc) / stack traces to clients」

**证据**：tasks.py:137 与 :167 `state.error = str(exc)`；该字段经 api/import_.py:_to_status → TaskStatusResponse.error 直接返回给 GET /api/tasks/{task_id} 客户端。

**触发场景**：扫描任务中 SQLAlchemy/OS 抛异常（如 `OperationalError: ... D:\...\picture_mangers.db`），轮询 /api/tasks/{id} 的前端会看到含本机绝对路径/内部实现细节的原始异常文本。

**最小修复**：worker 里 logger.exception 记录原异常，state.error 存一句通用中文提示（如「导入失败，请查看服务器日志」）或稳定 code。

**复核意见**：证据属实：tasks.py:137/:167 state.error = str(exc)，经 api/import_.py:28-38 _to_status 原样进入 TaskStatusResponse.error 返回客户端；项目规范明文禁止（quality-guidelines.md:25、error-handling.md:56「never return str(exc) to the client」）。无测试断言 error 字段被脱敏。属确凿的规范违背，但单用户本地部署下泄露对象是用户自己，实际危害有限，降为 low。最小修复：error 存日志，响应放通用消息。

## 37. [低] schema-field-consistency · backend/app/api/tags.py:35

**问题**：tags API 组装响应时传入 is_deprecated，但 TagResponse schema 没有该字段，Pydantic 默认 extra='ignore' 静默丢弃，字段永远不会到达客户端

**证据**：api/tags.py:30-36 `return TagResponse(..., is_deprecated=tag.is_deprecated,)`；schemas/post.py 的 TagResponse 只有 id/name/category/post_count；模型 models/tag.py:20 确有 `is_deprecated: Mapped[bool]`；前端 types.ts:20-25 Tag 也无此字段

**触发场景**：标签被弃用后（is_deprecated=true），GET /api/tags 与 /api/tags/{id} 的响应里完全看不到该状态，前端无法区分或灰显弃用标签；代码意图（传字段）与实际契约（丢弃）不一致，是静默漂移

**最小修复**：二选一并保持前后端同步：要么在 TagResponse 加 `is_deprecated: bool = False` 并同步 frontend/lib/types.ts 的 Tag；要么删掉 api/tags.py:35 这行死参数

**复核意见**：证据属实：api/tags.py:35 传 is_deprecated，而 TagResponse（schemas/post.py:9-13，经 schemas/tag.py 再导出）无该字段，Pydantic v2 默认 extra='ignore' 静默丢弃，backend/tests/ 无任何 is_deprecated 覆盖。但全代码库唯一写入点是模型默认值 False（models/tag.py:20），没有任何弃用端点/服务会把它置 True，场景仅在手改 DB 时可达，当前无用户可见影响。属真实的静默契约漂移，降为 low；最小修复：在 TagResponse 加 is_deprecated: bool 字段或删掉 _to_response 中该实参。

## 38. [低] missing-index · backend/app/models/post.py:43

**问题**：posts.rating 与 duplicate_of_id 无索引，safe_mode 下每次列表的 COUNT 全表扫描；favorite_items.post_id 反向查询也无索引

**证据**：post.py:39-43: rating 与 duplicate_of_id 均为普通列，__table_args__ (line 45-56) 只有 source 部分唯一索引；search.py:59 每次请求执行 `select(func.count()).select_from(stmt.subquery())`（rating='safe' + duplicate_of_id IS NULL 过滤）。favorite.py:24-29 复合主键 (favorite_id, post_id) 只能覆盖 favorite_id 前缀，按 post_id 查（toggle_star、上条修复的批量查询）走全表

**触发场景**：库达数万帖后，画廊每次翻页的 total 计数都对 posts 做全表扫描（分页主体靠 PK 排序尚可）；每次星标切换对 favorite_items 全扫。单用户 SQLite 下是毫秒~几十毫秒级退化，非硬伤但零成本可防

**最小修复**：加一条 Alembic 迁移：`Index('ix_posts_rating', 'rating')`（或复合 (rating, duplicate_of_id)）与 `Index('ix_favorite_items_post_id', 'post_id')`

**复核意见**：证据属实：post.py 的 __table_args__ 只有 source 部分唯一索引，rating/duplicate_of_id 无索引且无迁移补建；search.py:59 每次列表请求都对过滤后的子查询做 COUNT（safe_mode 下含 rating='safe' + duplicate_of_id IS NULL 全表扫描）；favorite_items 复合主键 (favorite_id, post_id) 无法覆盖 favorites.py:116/138/152/177 按 post_id 的查询。backend/tests 无相关性能/查询计划覆盖。单用户 SQLite 场景下仅为毫秒级退化，非硬伤，维持 low。最小修复：post.py 加 Index('ix_posts_rating','rating') 与 Index('ix_posts_duplicate_of_id','duplicate_of_id')（或复合部分索引），favorite.py 加 Index('ix_favorite_items_post_id','post_id')，并出一条 Alembic 迁移。

## 39. [低] spec-logging-guidelines · backend/app/services/errors.py:73

**问题**：整个 backend/app 没有任何 logging 调用；logging-guidelines 要求的日志点（catch-all 记 ERROR、登录成功/失败、长任务 started/finished、scraper 重试 WARNING）全部缺失

**证据**：grep 'logging|logger' 在 backend/app 下零命中。errors.py:73 `unhandled_exception_handler` 只返回 500 envelope 不记录 exc（规范：the catch-all handler also logs these）；scrapers/danbooru.py:_get 429/5xx 重试无 WARNING；services/tasks.py 任务开始/结束无 INFO。

**触发场景**：任意请求触发未预期异常 → 客户端收到通用 500，服务端无任何记录，异常现场完全丢失，无法排障；scraper 被限流重试也无迹可查。

**最小修复**：各模块加 `logger = logging.getLogger(__name__)`；unhandled_exception_handler 里 `logger.exception(...)`；按规范在 auth 登录/登出、任务生命周期、scraper 重试处补 key=value 风格日志。

**复核意见**：证据属实：backend/app 全目录零 logging 调用，而 scraper 重试、导入任务生命周期、登录事件等域事件日志点已由后续切片实现却未按 logging-guidelines 加日志（规范只豁免骨架期）。但场景描述夸大：main.py:34 用 add_exception_handler(Exception,...) 注册，Starlette ServerErrorMiddleware 发送响应后会重新抛出异常，uvicorn 仍打印完整堆栈，500 异常现场并未丢失。剩余缺口是域事件可观测性（scraper 被限流/任务进度无迹可查），单用户本地应用下降为 low。

## 40. [低] spec-type-hints · backend/app/deps.py:8

**问题**：`from app.models.user import Session, User` 遮蔽了上一行导入的 sqlalchemy.orm.Session，导致 deps.py / api/posts.py / api/auth.py 中所有 `db: Session` 注解实际指向 ORM 会话行模型（sessions 表），类型标注全部错误，违反「Type hints on all function signatures」

**证据**：deps.py:5 `from sqlalchemy.orm import Session` 后 deps.py:8 `from app.models.user import Session, User` 覆盖同名；api/posts.py:9/13、api/auth.py:11/16 同一模式。get_current_user(db: Session=...) 里 Session 已是 models.user.Session。

**触发场景**：mypy/pyright 一开严格模式即报错；阅读者/IDE 对 `db: Session` 推断出 sessions 表模型，补全与重构工具给出错误建议，埋下误用隐患（运行时因 Depends 恰好不校验才未爆）。

**最小修复**：统一改为 `from app.models.user import Session as SessionRow, User`（services/auth.py 已用此别名），注解处区分 SessionRow 与 orm Session。

**复核意见**：证据属实：deps.py:5 导入 sqlalchemy.orm.Session 后被 deps.py:8 的 app.models.user.Session 覆盖，get_current_user/get_current_session 的 `db: Session` 实际指向 sessions 表模型；api/auth.py:11/16 与 api/posts.py:9/13 同样模式（favorites/tags/import_ 只导 User，不受影响）。FastAPI 运行时不校验该注解故 63 例测试全绿并不能兜底，strict mypy/pyright 会报错且 IDE 推断错误。仅为类型标注/工具链问题，无运行时或安全影响，维持 low。最小修复：`from sqlalchemy.orm import Session as DbSession` 或给模型导入起别名（如 `Session as SessionModel`）。

## 41. [低] config-dead-default-secret · backend/app/config.py:30

**问题**：secret_key 有弱默认值 "dev-secret-change-me" 但全项目零处使用，属误导性死配置

**证据**：config.py:30 `secret_key: str = "dev-secret-change-me"`；grep 全 backend/app 仅此一处出现 secret_key。会话实际用 secrets.token_urlsafe(32) 随机 token 存 DB（app/services/auth.py:38），不做任何签名，secret_key 没有消费者

**触发场景**：无直接安全漏洞（token 不依赖它签名），但运维者会误以为改了 SECRET_KEY 就完成了加固；未来若有人拿它去签名/加密，弱默认值会静默成为真实漏洞

**最小修复**：删除 config.py 中的 secret_key 字段；若预留未来使用，改为无默认值必填（`secret_key: str`）让启动时显式报错

**复核意见**：证据属实：config.py:30 定义 secret_key="dev-secret-change-me"，全 backend 仅此一处出现（grep 确认零消费者）；会话认证走 services/auth.py:38 的 secrets.token_urlsafe(32) 随机 token 存 DB，不做签名。当前无实际漏洞，仅是误导性死配置——运维者可能误以为改它就完成加固，未来若被拿去签名会静默变成真漏洞。单用户局域网威胁模型下维持 low。最小修复：删掉该字段，或加注释/启动告警说明未使用。

---

## 已否决的指控（复核不成立，勿重复报告）

- **login-brute-force** @ backend/app/api/auth.py（out_of_scope）：事实成立（api/auth.py:56-64 无限流，全仓无 limiter），但威胁模型明确单用户本地/局域网部署、互联网级加固非必修；非认证绕过，bcrypt cost 12 已提供天然减速。按判定基准归入超出威胁模型。
- **scan-path-unrestricted** @ backend/app/services/import_service.py（out_of_scope）：证据属实（schemas/task.py 仅 min_length=1，无根目录白名单），但该应用的既定功能就是让唯一的 admin 用户扫描本机任意目录；触发场景依赖会话 cookie 泄露/他人复用浏览器，超出单用户本地/局域网威胁模型。非路径穿越（不能经 API 读任意文件内容，只是导入图片），不算认证绕过。
- **n-plus-one** @ backend/app/api/posts.py（refuted）：『favorite 硬编码 False』部分与 index 1 完全重复（同一行同一缺陷）；而 n-plus-one 指控本身针对的是『若将来按帖循环查』的假想修复方案——当前代码不存在任何逐帖 SELECT，N+1 不成立。规则名下的实际缺陷不存在，属推测性发现。
- **error-handling-catchall-no-logging** @ backend/app/services/errors.py（refuted）：场景不可达：虽然 errors.py:73 处理器体内确无 logger 调用，但 Exception 级 handler 经 Starlette ServerErrorMiddleware 执行——发送 envelope 响应后异常被重新 raise，uvicorn 的 error logger 记录 'Exception in ASGI application' 及完整 traceback。因此「服务端日志里没有任何堆栈或上下文、问题无法排查」不成立；且规范注明骨架期未加 app 级日志属已知状态。与 index 0 剩余可成立部分重复。

## 备注

- 高危前三条为去重后的独立根因；#1/#2/#7 等多条实为同一 rollback 缺失的不同表现，修一处 except 分支即全消。
- README 已知约束（Danbooru 真实抓取被 Cloudflare 拦截）不计入发现。
- 本报告仅记录，不含任何代码修改。