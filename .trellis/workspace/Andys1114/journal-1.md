# Journal - Andys1114 (Part 1)

> AI development session journal
> Started: 2026-06-28

---

## 2026-06-29 — 子任务 06-29-backend-skeleton 完成

**任务**: 后端骨架 + 数据模型 + 单用户认证(父任务 06-28-gallery-app 的子任务 1)

**完成内容**:
- FastAPI + SQLAlchemy 2.0 + SQLite(WAL) + Alembic 脚手架
- 8 张 ORM 表(posts/tags/post_tags/tag_implications/favorites/favorite_items/users/sessions)
- 单用户认证:首次 /setup 向导 + /login + /logout + /me,cookie 会话保护
- 统一错误信封 + CORS + 健康检查
- pytest 11 用例覆盖 AC1-AC12 全绿
- 填充 5 个后端 spec 文件(directory-structure/database-guidelines/error-handling/quality-guidelines/logging-guidelines)

**关键决策**:
- session 存 DB 而非 JWT —— 个人单用户场景,DB session 可即时失效(logout 删记录),实现简单
- Alembic 而非 create_all —— 为后续 7 个子任务的 schema 演进铺路
- 严格只做地基 + auth + health,不碰业务路由 —— 避免范围蔓延

**踩坑**:
- ZCode Bash 工具初期崩溃(0xC0000142,Cygwin fork),重装 Git for Windows + rebase 后恢复
- 长文本内联手写 design.md 时出现模型输出退化(乱码/重复),改用分段 Edit 写入规避
- alembic.ini 用 locale 编码(GBK)读取,不能含非 ASCII 注释
- 测试里 `from app.db import SessionLocal` 拿的是 patch 前引用,改用 `db_module.SessionLocal` 访问被 patch 的属性

**提交**: 2555ac0 / 05b90fb / 451c761 / 997b226
**状态**: 已归档至 archive/2026-06/

**下一步**: 父任务剩余 7 个子任务。建议下一个做子任务 2(标签搜索编译器)或子任务 3(媒体处理管道),两者都只依赖子任务 1,可并行。

---

## 2026-06-30 — grilling 会话 + 领域模型决策落地(子任务 06-30-domain-spec-landing)

**任务**: 用 `/grill-with-docs`(grilling + domain-modeling skill)对现有规范做压力测试,敲定领域模型并落地。

**完成内容**:
- grilling 一对一访谈,敲定 10 条领域决策:单用户语义(bootstrap-single-user)、标签连带/废弃(只有 implication 无 alias、is_deprecated 独立)、连带防环(写入前反向可达性+闭包带已访问集合)、post_count 语义、收藏(纯收藏夹+默认夹、不统计收藏次数)、重复图(md5+phash 异步、duplicate_of_id、主视图默认隐藏)、评级三档、连带时机(写入时算实)、搜索(本期仅 AND)、抓取去重(source_id 阶段+md5 兜底+部分唯一索引)。
- 建根目录 `CONTEXT.md`(中文术语表,5 组 14 词)。
- 建 `docs/adr/0001-implication-materialized-at-write-time.md`(连带写入时算实,最难反悔的决策)。
- 改 `.trellis/spec/backend/database-guidelines.md`:删 fav_count、post_count 改为 post_tags 行数、递归 CTE 改为仅写入时、新增重复图与抓取去重小节。
- 改 `.trellis/spec/backend/quality-guidelines.md`:加搜索/评级/重复图语义、禁用 fav_count、禁用读时递归搜索、补检查项。
- 回改父任务 `06-28-gallery-app` 的 prd.md 与 design.md 消解三处冲突:搜索语法本期仅 AND(NOT/OR/通配留后续)、fav_count 删除、连带机制改写入时算实。顺带对齐 F5/AC4 重复图、design.md 第 3 节查询编译流程与关键设计决策。

**关键决策**:
- 连带写入时算实而非读时递归——让 post_tags 永远是展开集,搜索变简单、post_count 永远准、删连带是"黏"的。这是 ADR-0001 的核心。
- 搜索本期砍到只做 AND——回退了原 PRD 的 NOT/OR/通配,用户确认留后续版本。
- 不统计收藏次数、删 Post.fav_count——回退了原 PRD 的冗余字段。

**待办(留给后续实现子任务)**: 一条 Alembic 迁移要删 Post.fav_count、加 Post.duplicate_of_id(自引用 FK,SET NULL)、加 (source_site,source_id) 部分唯一索引。

**状态**: 文档落地完成,待提交。

---

## 2026-06-30 — 前端 grilling + 前端 spec 落地(子任务 06-30-frontend-spec-landing)

**任务**: 用 `/grill-with-docs` 对前端做压力测试(前端要交给 `/ui-ux-pro-max` 建),敲定决策并落地。

**完成内容**:
- grilling 敲定 7 条前端决策:技术栈(Next 15 App Router + TS + Tailwind + shadcn/ui + lucide)、渲染取数(客户端为主 + TanStack Query,RSC 只做外壳/中间件)、详情页(`?photoId=` 软导航浮层,无独立 /post/[id] 路由,直达禁用翻页)、图片管线(FastAPI StaticFiles /media + Next rewrite 同源 + Next/Image unoptimized + tier loader,blur-up 暂缓)、安全模式(挂 Session、新会话默认开自动回安全)、鉴权流(中间件挡 cookie + /login /setup 调 /api/auth/status 分流 + provider 调 /api/me)、交付顺序(切片1 设计基座+浏览页+lightbox → 标签/搜索 → 收藏 → 导入/抓取 → 登录/设置;先补后端最小接口不造 mock;桌面优先+窄屏不崩,移动端后议)。
- 填满 `.trellis/spec/frontend/` 6 个空模板(directory-structure/component-guidelines/hook-guidelines/state-management/quality-guidelines/type-safety),index 全标 Filled。
- CONTEXT.md 补"前端界面"组(浏览页/详情页 Lightbox/安全模式)。
- 回改父 PRD:F1 安全模式挂 session、F2 详情页改 ?photoId 软导航、F8 鉴权流细化、第 5 节约束补前端栈。

**关键决策**:
- 详情页用 `?photoId` query param 软导航而非拦截路由——更简单、贴合 lightbox;翻页用 replace 避免后退地狱,直达场景关闭用 replace 抹参数(不能 back)。
- 安全模式挂 Session 不挂 User——实现"新会话自动回安全"的防误看语义。
- 前端不造 mock,等后端最小接口(posts 列表/单图/auth-status/me/media)就位再开切片1。

**待办(后端)**: 新接口 GET /api/posts、GET /api/posts/{id}、GET /api/auth/status、PATCH /api/me/settings、GET /api/me(含 safe_mode)、StaticFiles /media;迁移加 Session.safe_mode(默认 true),连同上一轮的 fav_count 删除/duplicate_of_id/来源唯一索引进同一条迁移。

**状态**: 文档落地完成,待提交。




## Session 1: 前端骨架+浏览页 与 最小后端端点

**Date**: 2026-07-01
**Task**: 前端骨架+浏览页 与 最小后端端点
**Branch**: `main`

### Summary

用 Trellis 工作流交付 06-30-frontend-skeleton-browse（父 design #5）。先补 spec 合规的最小后端端点（Session.safe_mode + migration、/api/auth/me + settings PATCH、/api/posts 列表/详情、/media StaticFiles、search AND 服务、NotFoundError、post schemas、test_posts 11 例，pytest 25/25 绿、dev seed 脚本），再前端真接零 mock（Next 15 + TS strict + Tailwind + shadcn 风格 UI + TanStack Query：鉴权流 middleware+providers+setup/login/settings、浏览页毛玻璃顶栏+搜索框+安全模式开关+CSS columns 瀑布流+无限滚动+卡片 hover；lint/tsc/build 干净、端到端联调通过）。期间 before-dev 拦截到方案违反 spec（禁前端 mock + safe_mode 服务端权威），改走先补后端端点路径并更新 spec。修复一处 dev server .next 缓存脏导致 main-app.js 404 卡在加载中的问题。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `085a07f` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: 前端视觉美化打磨

**Date**: 2026-07-01
**Task**: 前端视觉美化打磨
**Branch**: `main`

### Summary

用 Trellis 工作流交付 07-01-frontend-visual-polish：在已交付骨架上做纯 Tailwind/CSS 视觉打磨，零新依赖、不改功能契约（trellis-check 确认 api/types/hooks/middleware/providers 零修改）。改动：next/font 真正加载 Inter+JetBrains Mono（此前仅声明未加载）、补 elevation/shimmer/focus token；新建 AuthCard（径向渐变+品牌 wordmark）与 PasswordInput（show/hide）复用至 login/setup；settings 分三段卡片；顶栏 logo 加图标+滚动渐隐加 opacity；卡片 hover 微缩放+图片淡入+底部渐变遮罩+分级 chip（图标+标签+色，color-not-only）+★ 触屏始终可见；瀑布流 stagger 入场+shimmer skeleton+空态图标+错误重试；Button press 缩放+统一 ease-out。tsc/lint/build 全干净、e2e 冒烟通过、trellis-check PASS。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `df9e5fb` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: 媒体处理管道 + 最小 Post 摄入 (切片3)

**Date**: 2026-07-03
**Task**: 07-01-backend-media-pipeline（父任务 06-28-gallery-app 切片 3）
**Branch**: `main`

### Summary

用 Trellis 工作流推进后端「数据进不来」的卡点：交付 `services/media.py` 摄入内核（md5 精确去重、imagehash phash 同步算值存字段、Pillow thumb/preview 缩略图、动图取首帧保留动画、落盘 `posts/{id}/` 并写 Post 行），可被切片 4（抓取）/切片 8（导入 API）直接复用。迁移 `seed_dev.py` 用真管道造数（dev 库从此是真缩略图 + 真 phash）。零 schema 变更、零 API 端点、不做任务调度——纯可复用内核。决策点与用户敲定：边界=服务+最小Post写入（非纯函数，解 id 先有鸡先有蛋）、phash 用 imagehash 库（稳健性优先，接受新依赖）、phash 同步算值但查邻标记 duplicate 留异步（与 spec「phash 异步」调和：算值快、查邻慢）、md5 命中抛可恢复 DuplicateError、seed_dev 一并迁移。期间 imagehash 拉 scipy 55MB 在 hermes venv 反复超时，用户手动装好后继续。

### Main Changes

- `backend/app/services/media.py`（新增）：compute_md5 / compute_phash(imagehash) / make_thumbnails(150/850, RGB白底, ImageOps.contain) / ingest（11 步流程：md5→去重→Pillow解码→phash→缩略图→Post占位→flush拿id→建目录落盘→回填相对路径→commit；动图 seek(0) 首帧做缩略图、original 存原始 bytes 保留动画）。
- `backend/app/services/errors.py`：新增 DuplicateError(AppError) 409 code=duplicate。
- `backend/scripts/seed_dev.py`：删手写落盘+Post 构造，改循环调 media.ingest，DuplicateError 捕获后 continue 保幂等；目录结构 {md5}/→{id}/；清理无用 import。
- `backend/tests/test_media.py`（新增 6 例）：AC1 落盘+写库、AC2 md5去重、AC3 phash（纹理图对照 Hamming 距离，纯色图 DCT 退化不能测区分力）、AC4 缩略图尺寸+GIF首帧静态、AC6 落盘失败事务回滚。
- `backend/pyproject.toml`：加 pillow>=10.0 + imagehash>=4.3。
- 4 个 backend spec 回写：database-guidelines（dedup 契约精确化——phash 算值同步/查邻异步）、quality-guidelines（Domain Field Contract 状态）、error-handling（补 NotFoundError+DuplicateError）、directory-structure（services 实现状态+media.py 示例）。

### Git Commits

| Hash | Message |
|------|---------|
| `e10352b` | feat(backend): 媒体处理管道 + 最小 Post 摄入 (切片3) |
| (auto) | chore(task): archive 07-01-backend-media-pipeline |

### Testing

- [OK] pytest -q 全量 31 passed（原 25 + 新增 6 media），10.91s
- [OK] AC5 seed_dev 实跑：12 posts，phash 12/12 非空、preview≠original、目录 posts/{id}/
- [OK] spec 自查：无 fav_count 生产代码、无 create_all runtime、无 raw SQL、imagehash 记入 pyproject

### Key Decisions

- phash 算值同步/查邻异步：spec 原写「phash 异步后算」，本切片调和为「算 hash 值快→同步存字段；扫库找近邻慢→留切片4/8 调度器」。ingest 后 Post 的 phash 非空但 is_duplicate=False、duplicate_of_id=None。
- id 先有鸡先有蛋：ingest 先 flush（不发 INSERT 的 COMMIT 但拿自增 id）→ 用 id 建目录落盘 → 回填路径 → commit。落盘失败因未 commit，session 回滚不留半残行（AC6 验证）。
- 测试 fixture 教训：pHash 对纯色图退化（DCT 只有 DC 分量，不同纯色塌缩成同一 hash）——AC3 改用纹理图（梯度+棋盘 XOR）测区分力。GIF 多帧需每帧 RGB 内容不同，P mode 单色帧会被 Pillow 合并成 n_frames=1。

### Status

[OK] **Completed & archived → archive/2026-07/**

### Next Steps

- 父任务 06-28-gallery-app 剩余后端切片：切片 2 剩余（标签 implication 写入时物化 + post_count 维护 + tags CRUD/树端点）、切片 4（Danbooru 抓取器，复用本次 media.ingest）。两者都依赖本切片已交付的摄入内核。


## Session 4: 标签 implication 写入侧 + tags 端点 (切片2剩余)

**Date**: 2026-07-03
**Task**: 07-03-backend-tag-write-side（父任务 06-28-gallery-app 切片 2 剩余）
**Branch**: `main`

### Summary

用 Trellis 工作流交付标签系统写入侧：services/tags.py 实现 ADR-0001 三不变量——tag_post 算整条连带闭包(A→B→C)一次性写进 post_tags、create_implication 防环(反向可达性检查,自环/成环抛 ConflictError 409)+ 回填现有前因 post、post_count 写时 ±1 维护(复合主键去重幂等)。配套标签资源 CRUD 端点(GET 列表/tree/详情、POST、PATCH)。让标签系统从「读取侧能搜、写入靠 seed 手插」闭环到「打标签→物化→post_count 准→标签页有数据→可 CRUD」。为切片4(抓取)的「带回标签→物化入库」铺好复用入口(tag_post 服务函数)。决策点与用户敲定：打标签/implication 均只做服务不做端点(端点留给切片6详情页编辑)、回填同步、不做删除 implication / DELETE tag(黏语义)。闭包实现选 BFS+visited 而非递归 CTE(SQLAlchemy 2.0 在 SQLite 的递归 CTE 构造繁琐,BFS 语义等价、单用户量级够),spec 已回写偏差。

### Main Changes

- `backend/app/services/tags.py`（新增）：closure_of(BFS+visited,write-time only)、tag_post(get-or-create+闭包+写post_tags去重+post_count±1)、create_implication(自环检查+反向可达性防环+插入+回填)、create_tag/update_tag/list_tags/get_tag/tag_tree。
- `backend/app/api/tags.py`（新增）：GET /api/tags(搜索/类别/排序)、GET /api/tags/tree、GET /api/tags/{id}、POST、PATCH。route 薄调 service,全部 Depends(get_current_user)。/tree 在 /{id} 前注册避免路径捕获。
- `backend/app/schemas/tag.py`（新增）：复用 post.TagResponse,新增 TagCreateRequest/TagUpdateRequest/TagTreeNode/TagListResponse/TagTreeResponse。category 用正则约束(general/character/copyright/artist/meta)。
- `backend/app/schemas/__init__.py`：导出 tag schemas。
- `backend/app/api/__init__.py`：挂 tags.router。
- `backend/tests/test_tags.py`（新增 8 例）：AC1 物化闭包、AC2 防环、自环、AC3 回填、AC5 post_count幂等、AC6 CRUD端点(含401)、tree结构、AC7 端到端(ingest→tag_post→search搜到)。
- 2 个 backend spec 回写：directory-structure(services/api 加 tags)、database-guidelines(CTE→BFS 偏差明确化、post_count 维护流程、防环细节)。

### Git Commits

| Hash | Message |
|------|---------|
| `aca32ca` | feat(backend): 标签 implication 写入侧 + tags 端点 (切片2剩余) |
| (auto) | chore(task): archive 07-03-backend-tag-write-side |

### Testing

- [OK] pytest -q 全量 39 passed（原 31 + 新增 8 tags），10.15s
- [OK] AC1-AC7 + 自环全过；端到端(ingest Post→tag_post→GET /api/posts?tags= 搜到)闭环验证
- [OK] spec 自查：search.py 无读时递归、防环 409、route 薄调 service(6处)、无 create_all/raw SQL/fav_count

### Key Decisions

- 闭包 BFS 而非递归 CTE：spec 原偏好递归 CTE(write-time only),但 SQLAlchemy 2.0 在 SQLite 的递归 CTE 构造繁琐且易错。BFS+visited 语义等价、单用户量级性能够、visited 集合天然就是 ADR 要求的防环兜底。spec 已回写此偏差,未来量大可换回 CTE 不改调用方。
- 打标签/implication 只做服务不做端点：切片4 抓取调服务函数不走 HTTP;打标签端点的真实用户是详情页编辑(切片6 PATCH /api/posts/{id})。本切片聚焦物化闭环,不扩 API 表面。
- 不做删除(黏语义)：ADR-0001 删 implication 不撤老图标签,语义重;删 tag CASCADE post_tags 会丢打标记录。本切片只做创建,删除留后续。

### Status

[OK] **Completed & archived → archive/2026-07/**

### Next Steps

- 父任务 06-28-gallery-app 剩余后端切片：切片4(Danbooru 抓取器,复用本次 tag_post + 切片3 media.ingest,能端到端「抓取→入库→物化标签」)。写入侧与摄入内核均已就位,抓取器是最后一块数据进入拼图。


## Session 5: Danbooru 抓取器 (切片4)

**Date**: 2026-07-03
**Task**: 07-03-backend-danbooru-scraper（父任务 06-28-gallery-app 切片 4）
**Branch**: `main`

### Summary

用 Trellis 工作流交付后端「数据进入」最后一块拼图：scraper 抽象（scrapers/base.py：Scraper ABC + ScrapedPost/ScrapedTag dataclass）+ Danbooru 适配器（scrapers/danbooru.py：匿名公共 API、time.sleep 限速、指数退避重试、search/fetch/fetch_implications、按 API 文档字段映射）+ 编排服务（services/scrape.py：scrape_to_db 两阶段去重 source 列表查跳过下载 + md5 DuplicateError、download→media.ingest→tag_post、错误隔离单张失败不中断整批；bootstrap_implications 拉远程 implication 图复用 create_implication 防环409跳过）。复用切片3 media.ingest + 切片2剩余 tag_post/create_implication（不改只调）。决策点与用户敲定：Cloudflare 403 拦截 Danbooru 公共 API（JS challenge 非 UA 能绕）→ 全 mock 测试（FakeScraper + httpx.MockTransport），真实抓取留给用户配 HTTPS_PROXY 后 httpx 自动认、不在 AC 内；编排放 services/scrape.py 跨层胶水（scraper 只管 HTTP、orchestrator 只管 DB）；限速 time.sleep 非令牌桶（单线程单用户够）。

### Main Changes

- `backend/app/scrapers/base.py`（新增）：Scraper 抽象基类（search/fetch 抽象 + download 具体默认 httpx GET）、ScrapedPost/ScrapedTag dataclass、rate_limit_sleep 测试可 patch 包装。
- `backend/app/scrapers/danbooru.py`（新增）：DanbooruScraper——_get（限速+指数退避重试 429/5xx/网络错误，max_retries 耗尽抛 ScraperError）、search/fetch/fetch_implications、_parse_post 字段映射（id/file_url→image_url/file_ext/rating s/q/e/g→safe/questionable/explicit/tag_string_general|character|copyright|artist|meta→5类/animated 检测）。
- `backend/app/services/scrape.py`（新增）：ScrapeResult dataclass（new/duplicate/failed）、scrape_to_db（两阶段去重 + ingest + tag_post + 错误隔离）、bootstrap_implications（拉远程 implication 复用 create_implication 防环跳过）。
- `backend/app/services/errors.py`：加 ScraperError(AppError 502 code=scraper_error)。
- `backend/tests/test_scrape.py`（新增 7 例）：AC3 两阶段去重（source 跳过下载 + md5 DuplicateError）、AC4 ingest+物化、AC6 错误隔离、AC5 implication bootstrap（环跳过）、AC2 danbooru parser + 429 重试（httpx.MockTransport）+ 重试耗尽抛 ScraperError。
- 2 个 backend spec 回写：directory-structure（加 scrapers 包 + scrape service + scraper/orchestration 分层示例）、error-handling（补 ScraperError 错误类型）。

### Git Commits

| Hash | Message |
|------|---------|
| `fd29b17` | feat(backend): Danbooru 抓取器 (scraper 抽象 + danbooru 适配器 + 编排服务, 切片4) |
| (auto) | chore(task): archive 07-03-backend-danbooru-scraper |

### Testing

- [OK] pytest -q 全量 46 passed（原 39 + 新 7 scrape），14.13s
- [OK] AC1-AC6 全过；danbooru parser 字段映射 + 429 重试 + 重试耗尽 ScraperError 全验证
- [OK] spec 自查：scrapers/+services/scrape.py 不导入 fastapi（纯服务）、media.py/tags.py 未改（只调）、零 schema 变更（仍 3 迁移）、测试无真实网络请求

### Key Decisions

- Cloudflare 403 → 全 mock 测试：Danbooru 公共 API 被 Cloudflare JS challenge 拦截（非 UA/referer 能绕）。切片价值在抽象+编排逻辑，FakeScraper + httpx.MockTransport 能验证正确性。真实可达是运维问题（用户配 HTTPS_PROXY 后 httpx 自动认，代码不改）。AC 诚实标注「真实抓取不保证可达」。
- scraper/orchestration 分层：scrapers/ 只管 HTTP（取元数据+字节，不导入 fastapi/不碰 DB），services/scrape.py 是跨层胶水（调 scraper + media.ingest + tag_post + create_implication）。让 scraper 可独立测试、orchestrator 可换数据源。
- 限速 time.sleep 非令牌桶：单线程单用户场景，令牌桶过度工程。rate_limit_sleep 包装便于测试 patch 为 0。
- httpx.Client 注入：DanbooruScraper 构造接受 client 参数，测试注入 httpx.MockTransport 伪造响应，无真实网络。

### Status

[OK] **Completed & archived → archive/2026-07/**

### Next Steps

- 后端「数据进入路径」三件套（media.ingest + tag_post 物化 + scraper 编排）已全部就位。剩余父任务子任务偏前端：切片6（详情页 lightbox）、切片7（标签页+搜索框 chip）、切片8（导入页 + 收藏夹——导入页接 POST /api/import/scrape 端点 + APScheduler 后台调度 + /api/tasks/{id} 进度轮询，复用本次 scrape_to_db）。后端至此无纯后端切片剩余，后续后端工作随切片8 的导入 API 端点 + 任务调度展开。


## Session 6: 收藏夹 F7 (favorites 端点 + 星标 toggle, 切片8后端部分)

**Date**: 2026-07-03
**Task**: 07-03-backend-favorites（父任务 06-28-gallery-app F7）
**Branch**: `main`

### Summary

用 Trellis 工作流交付收藏夹(图集)全套后端：services/favorites.py（CRUD + 加项末尾position/移项/调序 + 默认夹懒创建 get_or_create_default + toggle_star 星标=加入/移出默认夹）、api/favorites.py（6 端点：GET列表精简/POST新建/GET详情含items/POST加项/DELETE移项/PATCH调序，全认证）、api/posts.py 加 POST /{post_id}/favorite 星标 toggle（挂 posts.py，语义是 post 上的动作，返回{favorited:bool}）。核心 F7 语义：默认收藏夹承载星标、一张图可同时在默认夹和命名夹、不统计收藏次数（无 fav_count，通过 favorite_items 成员判断）。决策点与用户敲定：星标单独 toggle 端点（高频单按钮，默认夹是内部概念前端无需知其id）、默认夹懒创建（首次星标时建，避免改setup）、position 加项末尾 max+1 调序直接赋值（不做紧凑化）、GET 列表精简不含 posts。期间修复 _next_position 的 0-falsy bug（max=0 被 `0 or -1` 当 None，导致第二个加项 position 仍 0）。

### Main Changes

- `backend/app/services/favorites.py`（新增）：DEFAULT_FAVORITE_NAME 常量、get_or_create_default（懒创建）、create/get/list_favorites（list 带 item_count）、list_items、add_item（校验 post 404 + 末尾 position + 复合PK 冲突 409）、remove_item/reorder_item（404）、toggle_star（get_or_create_default + 查成员 toggle）。
- `backend/app/api/favorites.py`（新增）：6 端点 route 薄调 service，全 Depends(get_current_user)。
- `backend/app/api/posts.py`：+POST /{post_id}/favorite 调 favorites.toggle_star。
- `backend/app/schemas/favorite.py`（新增）：FavoriteResponse(item_count)/Create/Item/Detail/Reorder/StarToggle。
- `backend/app/schemas/__init__.py`：导出 favorite schemas。
- `backend/app/api/__init__.py`：挂 favorites.router。
- `backend/tests/test_favorites.py`（新增 6 例）：AC1 CRUD+401、AC2 加移项+409、AC3 调序（交换避免同position）、AC4+AC5 星标toggle+默认/命名独立、AC6 无fav_count、AC7 404。
- directory-structure spec 回写（services+api 加 favorites）。

### Git Commits

| Hash | Message |
|------|---------|
| `2d286a5` | feat(backend): 收藏夹 F7 (favorites 端点 + 星标 toggle, 切片8后端部分) |
| (manual) | chore(task): archive 07-03-backend-favorites（GPG签名失败，手动禁用签名提交） |

### Testing

- [OK] pytest -q 全量 52 passed（原 46 + 新 6 favorites），12.10s
- [OK] AC1-AC7 全过；星标 toggle + 默认/命名独立 + 无 fav_count 验证
- [OK] spec 自查：无 fav_count（仅 schema 注释提及）、route 薄调 service（8处）、零 schema 变更（仍3迁移）

### Key Decisions

- 星标单独 toggle 端点：星标是高频单按钮动作，toggle 最贴合 UX；默认夹是系统内部概念（CONTEXT.md），前端无需知其 id。挂 posts.py 而非 favorites router（语义是 post 上的动作，避免 router prefix 冲突）。
- 默认夹懒创建：首次星标时建（name=约定常量"默认收藏"，无 is_default 字段不改 schema），避免改 setup 逻辑；单用户无并发。
- position 0-falsy bug 教训：`(max_pos or -1)+1` 在 max_pos=0 时把 0 当 falsy → -1+1=0，第二个加项 position 仍 0。改用 `max_pos if max_pos is not None else -1`。Python 的 `or` 对 0/空字符串等 falsy 值要小心。
- 调序不做紧凑化：单用户量级，同 position 顺序未定义，前端按 position 排序；测试用交换（p1→1、p2→0）避免同 position 断言不稳。

### Status

[OK] **Completed & archived → archive/2026-07/**

### Next Steps

- 后端剩余端点：post 编辑/删除/next（切片6后端依赖）、import 任务调度+进度端点（切片8，接已交付 scrape_to_db）。父任务后端能力基本就位（auth/posts/tags/favorites/scrape/media），剩 post 编辑删除 + 导入任务调度两块。


## Session 7: post 编辑/删除/next 端点 (切片6后端)

**Date**: 2026-07-03
**Task**: 07-03-backend-post-edit（父任务 06-28-gallery-app 切片6后端）
**Branch**: `main`

### Summary

用 Trellis 工作流交付详情页 lightbox 的后端依赖：services/post_edit.py（update_post 全量替换标签——差集加调 tag_post 物化 + 差集删 post_tags + post_count-1、改 rating、部分更新；delete_post 删物理文件 rmtree + db.delete 级联 post_tags/favorite_items；next_post id desc 相邻排重图返回 prev/next id）、api/posts.py 加 PATCH/DELETE/GET /next 三个端点（全认证 route 薄调 service）、schemas/post.py 加 PostUpdateRequest + PostNextResponse。复用 tag_post 做加标签（物化闭包），补「移除标签」逻辑在 post_edit（删 post_tags 不撤 implication，ADR-0001 黏语义只针对 implication 关系本身，per-post 删标签安全）。决策点与用户敲定：标签全量替换（编辑心智是完整新列表，前端无需算 add/remove）、DELETE 删物理文件（避免孤儿堆积，文件删在 DB 删前失败可重试）、next 全局 id desc 不过滤（design §6 未提过滤，详情页翻页是全局浏览上下文）。

### Main Changes

- `backend/app/services/post_edit.py`（新增）：update_post（全量替换：差集加 tag_post 物化 + 差集删 post_tags + post_count-1；改 rating；部分更新）、delete_post（rmtree 物理文件 + db.delete 级联）、next_post（id desc 相邻，排重图 duplicate_of_id IS NOT NULL，prev/next）。
- `backend/app/api/posts.py`：+PATCH /{post_id}（改标签/分级）、+DELETE /{post_id}（删）、+GET /{post_id}/next（翻页上下文），全 Depends(get_current_user)。
- `backend/app/schemas/post.py`：+PostUpdateRequest(tags?/rating? pattern)、+PostNextResponse(prev_id?/next_id?)，补 Field import。
- `backend/tests/test_post_edit.py`（新增 5 例）：AC1 全量替换标签+post_count±1、AC2+AC3 rating/部分更新、AC4 删post+级联+文件+404、AC5 next翻页(首尾null)、AC6 401。
- database-guidelines spec 回写（post_count 维护补 post_edit 删减路径）。

### Git Commits

| Hash | Message |
|------|---------|
| (feat) | feat(backend): post 编辑/删除/next 端点 (切片6后端) |
| (auto) | chore(task): archive 07-03-backend-post-edit |

### Testing

- [OK] pytest -q 全量 57 passed（原 52 + 新 5 post_edit），14.38s
- [OK] AC1-AC6 全过；全量替换标签物化正确、删post级联+文件、next翻页首尾null
- [OK] spec 自查：复用 tag_post 未重写（post_edit 第69行）、route 薄调 service（3处）、零 schema 变更（仍3迁移）

### Key Decisions

- 标签全量替换：「编辑标签」心智是完整新列表，前端传完整 tags，服务端算差集（加调 tag_post 物化、删 post_tags + post_count-1）。比增量（add_tags/remove_tags）更直观，前端无需算差集。
- 删 post_tags 不撤 implication：ADR-0001 黏删除针对 implication 关系本身（删 implication 不撤老图标签）；per-post 删 post_tags 行只影响这个 post 的标签集，不影响其他 post 或 implication 关系。全量替换删差集安全。
- DELETE 删物理文件在 DB 删前：文件删失败时 post 仍在可重试；反之 DB 删了文件留孤儿指向不存在文件更糟。rmtree 失败抛异常，DB 未删。
- next 全局 id desc 不过滤：design §6 说「翻页上下文」未提过滤；详情页翻页是全局浏览，不是搜索结果内翻页。排重图仍排除（与列表视图一致）。

### Status

[OK] **Completed & archived → archive/2026-07/**

### Next Steps

- 后端只剩 import 任务调度（切片8）：POST /api/import/scan + /import/scrape + GET /api/tasks/{id} + APScheduler 后台调度，接已交付 scrape_to_db。这是最后一块后端。其余父任务子任务偏前端（切片6详情页 lightbox、切片7标签页+搜索框、切片8导入页UI+收藏UI）。


## Session 8: import 任务调度 + 进度端点 (切片8后端, 后端最后一块)

**Date**: 2026-07-03
**Task**: 07-03-backend-import-tasks（父任务 06-28-gallery-app 切片8后端）
**Branch**: `main`

### Summary

用 Trellis 工作流交付后端最后一块：import 任务调度 + 进度端点。services/tasks.py（APScheduler BackgroundScheduler max_workers=3 调度内核 + 内存任务状态 dict+Lock + submit_scan/submit_scrape/get_task/cancel_task 协作式取消 + 后台线程独立 SessionLocal 线程安全）、services/import_service.py（本地扫描编排：递归 walk + stat mtime 查 scan_history 跳过未变 + 读 bytes → media.ingest + 更新 scan_history + 进度更新）、api/import_.py（避开 import 关键字，4 端点 POST /import/scan、POST /import/scrape、GET /tasks/{id}、POST /tasks/{id}/cancel，全认证 route 薄调 service）、models/scan_history.py + 迁移 ffcb2b9d04bb（scan_history 表 path unique+mtime+scanned_at，可逆）、main.py（BackgroundScheduler 启动+shutdown 钩子）。复用 scrape_to_db + media.ingest 不改只调。决策点与用户连续拍板取完整方案：APScheduler（非 threading）、scan_history 表增量（非全扫md5去重）、多任务并行（max_workers=3 非串行）、任务取消做（非首版不做）、scrape 测 FakeScraper 注入。测试用 patch 同步 scheduler（add_job 直接调函数）避免异步测试复杂。

### Main Changes

- `backend/app/services/tasks.py`（新增）：TaskState dataclass + _tasks dict+_tasks_lock + BackgroundScheduler 单例(max_workers=3) + submit_scan/submit_scrape/get_task/cancel_task + _run_scan/_run_scrape（后台线程独立 SessionLocal，延迟 import 避免循环）。
- `backend/app/services/import_service.py`（新增）：scan_directory（递归 walk + SUPPORTED_EXTS + stat mtime 查 scan_history 跳过 + 读 bytes → media.ingest + 更新 scan_history + 进度 + is_cancelled 检查）。
- `backend/app/api/import_.py`（新增）：4 端点 route 薄调 tasks service，全 Depends(get_current_user)。
- `backend/app/models/scan_history.py`（新增）+ 迁移 ffcb2b9d04bb：ScanHistory(id/path unique/mtime/scanned_at)。
- `backend/app/main.py`：+BackgroundScheduler shutdown 钩子（on_event，deprecation 警告但功能正常）。
- `backend/app/schemas/task.py`（新增）：Scan/Scrape/TaskCreate/TaskStatus/TaskCancel。
- `backend/pyproject.toml`：+apscheduler>=3.10。
- `backend/tests/test_import_tasks.py`（新增 6 例）：patch 同步 scheduler，AC2+AC3 scan端到端+增量、AC4 scrape fake、AC5 取消、AC6 并发、AC7 401。
- 2 个 backend spec 回写：directory-structure（加 import_/tasks/import_service/scan_history + import_ 命名说明）、database-guidelines（加 scan_history 表 + 后台线程独立 session 约束）。

### Git Commits

| Hash | Message |
|------|---------|
| (feat) | feat(backend): import 任务调度 + 进度端点 (切片8后端, 后端最后一块) |
| (auto) | chore(task): archive 07-03-backend-import-tasks |

### Testing

- [OK] pytest -q 全量 63 passed（原 57 + 新 6 import_tasks），19.02s
- [OK] AC1-AC7 全过；scan端到端+增量跳过+scrape fake+取消+并发+401
- [OK] spec 自查：复用 scrape_to_db/media.ingest、route 薄调 service（7处）、后台线程独立 SessionLocal（2处）、scan_history 迁移可逆、apscheduler 记入 pyproject

### Key Decisions

- APScheduler（非 threading）：用户拍板取完整方案。BackgroundScheduler max_workers=3 多任务并行。main.py shutdown 钩子避免阻塞进程退出。
- scan_history 表增量（非全扫md5去重）：用户拍板。stat mtime 跳过未变文件，避免重读 bytes。新表+迁移，可逆。
- 多任务并行（max_workers=3）：用户拍板。SQLite WAL 单写者并行写串行等待，但启动不阻塞。
- 任务取消协作式：cancel_requested 标志 + worker 循环检查退出，status=cancelled。
- 测试 patch 同步 scheduler：add_job 直接调函数，避免异步轮询测试。取消测试用 _Deferred scheduler 手动控制执行时机。
- 后台线程独立 SessionLocal：SQLAlchemy session 非线程安全，worker 建 own session，每文件 commit 保持短事务 + 进度持久化。

### Status

[OK] **Completed & archived → archive/2026-07/**

### Next Steps

- **后端全部交付完毕**。父任务 06-28-gallery-app 后端端点全齐（auth/posts/tags/favorites/import+tasks，28 个端点 + 服务层 media.ingest/tag_post/scrape_to_db/post_edit/favorites/tasks/import_service）。剩余父任务子任务全偏前端：切片6（详情页 lightbox）、切片7（标签页+搜索框chip）、切片8（导入页UI+收藏UI，接本次 import/tasks 端点 + favorites 端点）。后端无更多纯后端切片，后续工作转前端。


---

## 2026-07-04 · 07-03-ui-spec-polish（UI 规范打磨）

### What Happened

- 多智能体三段流水线完成全前端 UI 规范打磨：审计（10 维度 x 34 文件 + 按文件对抗复核，31 agents，raw 98 → 确认 92：10 high / 28 medium / 54 low，否决 5）→ 实施（13 个文件互斥工作包并行，23 文件 +338/-149）→ 检查（5 组闭环核对 + 3 个 trellis-check 回归猎手：0 missed，7 partial 与 6 条新回归全部在主会话补修）。
- 十条 high 全修：--accent 调深 #2563eb（按钮白字 3.63→5.17:1）、顶栏 focus-within 键盘唤回（一处清四条同根）、Sheet 焦点圈闭/还原/X 钮/滚动锁、瀑布流 CSS columns → JS 贪心分列（追加页零重排）、search-box min-w-0（375px 溢出根因）、router.replace → push + 同步守卫。
- 运行时冒烟（curl SSR）：登录/画廊/设置三页全部命中新改动标记；tsc + lint 绿。

### Key Decisions

- 瀑布流弃 CSS columns：column-fill balance 每追加一页整列重排（复核员确认无纯 CSS 解法），改组件内贪心分列（前缀稳定），tab 顺序仍列优先（记入 spec Known Deferred）。
- --explicit 不动（兼任错误文本色），destructive 按钮局部改 bg-red-600；tagCategoryColor 的 text-accent 对比度隐患记入 spec 备忘（当前零调用点，接线时用 *-300 亮色）。
- 评分角标 scrim bg-black/40 → /90（白图最劣 explicit 4.65:1 达标）；text-[11px] → text-xs。
- 菜单项禁用态用 disabled:cursor-not-allowed 而非 pointer-events-none（后者让点击穿透误关菜单）。
- html 加 scrollbar-gutter: stable（滚动锁不再 17px 跳动）；masonry 列数惰性初始化（回退导航不整格重挂）。
- 用户可见文案全面去黑话（工单号/接口名/实现机制），规则沉淀进 component-guidelines Copy 节。

### Status

[OK] 92 条确认项：83 fixed + 7 partial 补修完 + 1 recorded（虚拟化，架构级）+ 0 missed；回归 6 条全修。待 commit。

### Next Steps

- 建议真人过一遍交互走查（键盘全流程 + 三档宽度），静态复核已覆盖但浏览器实操未做。
- 前端切片继续：切片6 lightbox / 切片7 标签chip / 切片8 导入UI（接已交付后端端点）。
