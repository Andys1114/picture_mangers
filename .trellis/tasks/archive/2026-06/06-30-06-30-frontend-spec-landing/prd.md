# 落地前端设计决策到前端 spec 并回改父 PRD

> 只描述需求、约束与验收标准。来源：2026-06-30 前端 `/grill-with-docs` 会话敲定的 7 条决策。

## 1. 背景

前端 grilling 敲定了 7 条决策（技术栈、渲染取数、详情页软导航、图片管线、安全模式、鉴权流、交付顺序）。决策已部分落进 `CONTEXT.md`（前端界面术语）。但 `.trellis/spec/frontend/` 6 个文件仍是空模板，父 PRD 前端段仍待细化。本任务填前端 spec、回改父 PRD、记录后端待补接口清单。**只改文档，不写前端/后端代码。**

## 2. 目标

1. 填 `.trellis/spec/frontend/` 的 6 个空模板（directory-structure / component-guidelines / hook-guidelines / state-management / quality-guidelines / type-safety），内容来自 7 条决策。
2. 回改父 PRD `06-28-gallery-app/prd.md` 前端段。
3. 在前端 spec 中记录后端待补接口/契约清单。

## 3. 验收标准

### AC1. directory-structure.md
- [ ] 写明：Next.js 15 App Router 目录结构（`app/` 路由 + `components/` + `lib/` + `hooks/` + `styles/`）；前端独立进程在 `frontend/`；命名约定。

### AC2. component-guidelines.md
- [ ] 写明：shadcn/ui 组件源码进项目、可改；lucide 图标；服务端组件仅做外壳/布局、客户端组件做交互；标签分类配色 token（character 蓝/copyright 紫/artist 黄/general 灰/meta 青）；毛玻璃顶栏、深色主题。

### AC3. hook-guidelines.md
- [ ] 写明：TanStack Query 为取数库；`useInfiniteQuery` 无限滚动、`useQuery`+`refetchInterval` 轮询任务进度、`useMutation` 乐观更新+失效；`useSearchParams` 驱动 lightbox `?photoId`。

### AC4. state-management.md
- [ ] 写明：服务端状态走 TanStack Query；本地 UI 状态走 React state/URL searchParams（lightbox photoId、左侧抽屉开关）；safe_mode 状态来自后端 session（不本地持久化）；不引入 Redux/Zustand。

### AC5. quality-guidelines.md
- [ ] 写明：TypeScript strict；禁用 `any`（必要时 `unknown`+类型守卫）；可访问性（键盘导航、焦点管理、alt）；深色主题对比度；不造 mock（前端等后端最小接口）。

### AC6. type-safety.md
- [ ] 写明：API 响应类型从后端 schema 派生或手写 TS interface 与后端 Pydantic 对齐；运行时校验入口（zod 可选）；fetch 层类型化。

### AC7. 后端待补清单
- [ ] 在 `state-management.md` 或 `hook-guidelines.md` 附"后端待补接口清单"：`GET /api/posts`、`GET /api/posts/{id}`、`GET /api/auth/status`、`PATCH /api/me/settings`、`GET /api/me`(含 safe_mode)、StaticFiles 挂 `/media/*`；迁移项 `Session.safe_mode`。

### AC8. 父 PRD 回改
- [ ] `F1`：安全模式开关注明"状态挂 session、新会话默认开、自动回安全"。
- [ ] `F2`：详情页改为 `?photoId=` 软导航浮层（push/replace/back/刷新自动开），去掉"独立路由"暗示；直达禁用 ← →。
- [ ] `F8`：补中间件 cookie 挡截 + /login、/setup 调 `/api/auth/status` 分流 + provider 调 `/api/me`。
- [ ] 第 5 节约束补：前端栈 Next.js 15 App Router + TS + Tailwind + shadcn/ui + lucide + TanStack Query。

## 4. 约束

- spec 文件用英文（沿用 `.trellis/spec/` 既有约定）；父 PRD 沿用中文。
- 不创建/修改任何 `.py`、`.tsx`、迁移文件。
