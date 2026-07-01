# 前端骨架 + 浏览页瀑布流 — PRD（spec 合规修订版）

> 父任务：`06-28-gallery-app`，对应父 `design.md` 第 8 节 #5。本版按 `.trellis/spec/frontend/*` 修订：**禁止前端 mock 服务端数据、禁止本地持久化 safe_mode**，故先补最小后端端点，前端再真接。技术设计见 `design.md`。

## 1. Goal / 用户价值

从 0 搭起前后端可联调的画廊骨架：补齐浏览页所需的最小后端端点（posts 列表/详情、/me 带 safe_mode、settings PATCH、/media 静态），再交付前端「首次向导 → 登录 → 深色瀑布流浏览页（顶栏 + 搜索框 + 安全模式开关 + 无限滚动）」，全部走真接口、零 mock。

## 2. 已确认事实（代码/spec 探查）

- **前端栈**：Next.js 15 App Router + TS + Tailwind + shadcn/ui + lucide-react + TanStack Query（服务端数据）。**无 Zustand**——UI 状态用 React state/Context，safe_mode 服务端权威（见 `state-management.md`）。
- **后端栈**：FastAPI + SQLAlchemy 2.0 + SQLite WAL + Alembic；分层 api/services/models/schemas；`AppError` 统一信封；`get_db`/`get_current_user` deps。
- **后端已就绪**：auth 全套（`/api/auth/status|setup|login|logout|me`，cookie `gallery_session`）；models（user/tag/post/favorite）+ 2 个 migration；health。
- **后端缺口（本期补）**：posts 列表/详情 API、search AND 编译器、`/media` 静态、`Session.safe_mode` 字段、`/me` 返 safe_mode、settings PATCH。Pillow 未装（dev seed 手写 PNG，不走媒体管道）。
- **spec 硬约束**：search 仅 AND over `post_tags`（无读时递归，ADR-0001）；默认排除 `duplicate_of_id IS NOT NULL`；rating 默认 safe；safe_mode 从 session 注入；无 `fav_count`；每条 AC 至少一个测试。
- **环境**：Node 24 / npm 11；Python 3.11+；`frontend/` 不存在。

## 3. 范围

### 后端 In scope（最小端点，spec 合规）
- `Session.safe_mode` 字段 + migration（默认 true）；新会话/登录默认 true。
- `NotFoundError`(404) 错误类型。
- `GET /api/auth/me` 返 `MeResponse{id, username, safe_mode}`；`PATCH /api/auth/me/settings {safe_mode}` 更新当前 session。
- `app/services/search.py`：`list_posts`（tags AND over post_tags、rating 过滤、safe_mode 注入、默认排除重复、id 倒序、page+limit 分页、total）；`get_post`（含展开 tags，404）。
- `app/api/posts.py`：`GET /api/posts?tags=&page=&limit=&order=`、`GET /api/posts/{id}`。
- `app/schemas/post.py`：PostSummary / PostDetail / TagResponse / PageMeta / PostListResponse。
- `main.py` 挂 `StaticFiles` at `/media` → `settings.media_path`。
- `backend/scripts/seed_dev.py`：dev-only，建 user（若无）+ 插 ~12 条真 Post（手写 PNG，含 rating/tags 变化），让浏览页可视觉验证。非生产代码、不进 pytest。

### 前端 In scope（真接，零 mock）
- Next.js 15 脚手架（`frontend/`，TS+Tailwind+App Router，无 src/）、shadcn/ui、lucide-react、design token（深色沉浸）。
- `lib/api.ts`（typed client，`credentials:'include'`，唯一 URL 处）、`lib/types.ts`（镜像后端 schema）、`lib/queryClient.ts`（QueryClient + key factory）。
- 鉴权流（真）：`/setup`、`/login`、`middleware.ts` cookie 门、providers 调 `/api/auth/me`（含 safe_mode）。
- 浏览页 `/`：顶栏（毛玻璃+滚动渐隐）、搜索框（基础结构，chip/补全留 #7）、MasonryGrid（CSS columns）、卡片 hover（收藏 ★ 本地乐观视觉 + 分级色块）、无限滚动（IntersectionObserver）、安全模式开关（真接 `/api/auth/me/settings`）。
- 标签抽屉**壳**（标签数据无来源，空态，#7 接）。

### Out of scope
- lightbox（#6）；搜索 chip/补全 + `/tags`（#7）；导入/收藏夹后端 + UI（#8）；媒体处理管道 md5/phash/缩略图生成（#3）；Danbooru 抓取（#4）；`/api/posts/{id}/next`（#6 翻页用）；favorites 真接口（#8，本期 ★ 仅本地视觉）。

## 4. 验收标准

### 后端
- [ ] `Session.safe_mode` migration 可 upgrade/downgrade；新 session 默认 true。
- [ ] `GET /api/auth/me` 返 `{id, username, safe_mode}`；未登录 401。
- [ ] `PATCH /api/auth/me/settings {safe_mode:false}` 更新生效，`/me` 反映；未登录 401。
- [ ] `GET /api/posts` 未登录 401；登录后返 `{data:[...], meta:{page,total}}`，默认 40/页、id 倒序。
- [ ] safe_mode=true 时列表只返 rating=safe（即便 DB 有 questionable/explicit）。
- [ ] `duplicate_of_id IS NOT NULL` 的图默认不出现。
- [ ] tags AND：`?tags=miku vocaloid` 只返同时含两标签的图（implication 已写入算实，命中展开集）。
- [ ] `GET /api/posts/{id}` 返详情含 tags；不存在 404 `not_found`。
- [ ] `/media/posts/...` 能取到静态图。
- [ ] `pytest -v` 全绿，每条 AC 有测试。

### 前端
- [ ] `cd frontend && npm run dev` 起来；DB 无 user → 受保护路由跳 `/setup`；建用户进 `/`。
- [ ] `/login` 登录；未登录访问 `/` → `/login?next=...`；登录后回 next。
- [ ] `/setup`（有 user 时）跳 `/login`；`/login`（无 user 时）跳 `/setup`（均 `/api/auth/status` 驱动）。
- [ ] 顶栏毛玻璃 + 滚动渐隐；含 Logo、搜索框、安全模式开关、设置入口。
- [ ] 浏布页无边框瀑布流（CSS columns，gap 4px），深色主题，图片来自真 `/api/posts` + `/media`。
- [ ] 卡片 hover 浮现 ★ + 分级色块（safe/questionable/explicit 三色）。
- [ ] 无限滚动加载下一页（IntersectionObserver）。
- [ ] 安全模式开关真接 `/api/auth/me/settings`，切换即时失效 posts 查询；默认开。
- [ ] `lib/api.ts` 唯一 URL 处；组件不硬编码 `/api/...`；无 mock 数据。
- [ ] TS strict + `npm run lint` + `npm run build` 通过。
- [ ] 响应式：375px 不横向滚动；触控目标 ≥44px；reduced-motion 降级。

## 5. 约束

- 严格遵循 `.trellis/spec/{backend,frontend,guides}/*`。
- UI 文本中文；代码标识符/注释英文；`alembic.ini` 纯 ASCII。
- 图标 lucide-react，不用 emoji；`<button>`/`<a>` 不用 `<div onClick>`。
- 深色沉浸配色按父 design §5。
- 后端 `http://localhost:8000`；Next rewrite `/api/*`、`/media/*` 同源代理，cookie 自动携带。
