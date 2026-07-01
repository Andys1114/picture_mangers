# 执行计划（spec 合规修订版）

> 阶段 B 后端先行（pytest 绿）→ 阶段 F 前端真接。每步带验证。

## 验证命令

```bash
# 后端
cd backend && pytest -v
python -m scripts.seed_dev          # dev seed
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm run lint && npx tsc --noEmit && npm run build
npm run dev                          # :3000
```

## 阶段 B — 后端最小端点

### B1. Session.safe_mode
- [ ] `models/user.py` Session 加 `safe_mode: Mapped[bool]`（default True, nullable False）。
- [ ] `services/auth.py` `create_session` 显式置 safe_mode=True；加 `get_session_row(db, token) -> SessionRow | None`。
- [ ] migration `add_session_safe_mode`（batch add_column + server_default "1"，可 downgrade）。
- [ ] 验证：`alembic upgrade head` + `downgrade -1` + `upgrade head` 不报错。

### B2. 错误 + schemas
- [ ] `services/errors.py` 加 `NotFoundError`（404, "not_found"）。
- [ ] `schemas/auth.py` 加 `MeResponse`、`UpdateSettingsRequest`；`schemas/__init__` 导出。
- [ ] `schemas/post.py` 新增 TagResponse/PostSummaryResponse/PostDetailResponse/PageMeta/PostListResponse；`schemas/__init__` 导出。

### B3. Deps
- [ ] `deps.py` 加 `get_current_session(request, db) -> Session`（None → UnauthorizedError）。

### B4. search service
- [ ] `services/search.py`：`list_posts`（duplicate_of_id IS NULL、safe_mode→rating safe、tags AND via post_tags、id desc、page/limit、total）、`get_post`（404）、`tags_for_post`。
- [ ] `services/__init__` 导出 search。

### B5. routes
- [ ] `api/auth.py`：`/me` 改用 `get_current_session` 返 `MeResponse`；新增 `PATCH /me/settings`。
- [ ] `api/posts.py`：`GET /`、`GET /{id}`。
- [ ] `api/__init__.py` 挂 posts router。
- [ ] `main.py` mount `/media` StaticFiles + mkdir。

### B6. 测试
- [ ] `tests/test_posts.py`：空列表、seed 列表、AND、safe_mode 注入、重复隐藏、分页、详情、404、未登录 401。
- [ ] `tests/test_auth.py` 增 `/me` 含 safe_mode、`PATCH /me/settings` 生效；确认既有子集断言不破。
- [ ] 验证：`pytest -v` 全绿。

### B7. dev seed
- [ ] `scripts/seed_dev.py`：幂等建 user + ~12 Post（手写 PNG，rating/tag 变化，含 miku→vocaloid implication）。
- [ ] 验证：`python -m scripts.seed_dev` 跑通；`uvicorn` 起，curl `/api/posts`（带 cookie）返数据。

## 阶段 F — 前端真接

### F1. 脚手架
- [ ] `npx create-next-app@latest frontend`（TS/Tailwind/ESLint/App Router/无 src/`--use-npm`）。
- [ ] `npm i @tanstack/react-query lucide-react`。
- [ ] `npx shadcn@latest init` + add button/input/skeleton/sheet/dropdown-menu/tooltip/sonner/badge。
- [ ] `next.config.ts` rewrite `/api/*`、`/media/*` → `http://localhost:8000`。
- [ ] `styles/globals.css` design token + Tailwind；`tailwind.config.ts` 暗色 fixed。
- [ ] 验证：`npm run dev` 起得来。

### F2. 类型 + API + queryClient
- [ ] `lib/types.ts`（design §2.2）。
- [ ] `lib/queryClient.ts`（key factory）。
- [ ] `lib/api.ts`（request + api.*，无 mock）。
- [ ] 验证：`npx tsc --noEmit`。

### F3. Hooks
- [ ] useMe/useSetup/useLogin/useLogout/useInfinitePosts/useUpdateSafeMode。
- [ ] 验证：`npx tsc --noEmit`。

### F4. 鉴权流
- [ ] `middleware.ts`、`providers.tsx`、`layout.tsx`、`setup/page.tsx`、`login/page.tsx`、`settings/page.tsx`。
- [ ] 验证：DB 空→`/`跳`/setup`；建用户进`/`；登出再访问跳`/login`。

### F5. 浏览页
- [ ] topbar/search-box/safe-mode-toggle/post-card/masonry-grid/tag-drawer。
- [ ] `(protected)/layout.tsx`、`(protected)/page.tsx`。
- [ ] 验证：`/`显示真瀑布流；滚动加载；安全模式切换重取；hover ★+色块。

### F6. 质量
- [ ] `npm run lint`、`tsc --noEmit`、`npm run build` 通过。
- [ ] 375px 不溢出；触控 ≥44px；reduced-motion 降级。
- [ ] 对照 `frontend/quality-guidelines.md` 自查 forbidden。
- [ ] 跑 trellis-check 过质量门。

## 风险/回滚

- shadcn init 失败 → 手写 components.json + lib/utils.ts（cn）。
- `create-next-app` 默认 Turbopack 出问题 → next.config 切换。
- 后端 migration 不可逆 → 先 `alembic downgrade` 测回滚再提交。
- 回滚：后端 downgrade + 撤新文件；前端删 `frontend/`。
