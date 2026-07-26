# 前台基座与切换

父任务：`07-26-frontend-redesign`（决策背景、子任务地图见父任务 prd.md）。
设计稿：`docs/design/pm-gallery-redesign/`（README.md 为权威规格；本任务对应 `final-front.dc.html`、`final-mobile.dc.html` 前 4 屏、`final-states.dc.html`）。

## Goal

完成前端目录切换（旧前端存档为 `frontend-legacy/`），并在新 `frontend/` 里把"暗房霓虹"前台基座搭到**日常可用**：登录/初始化、浏览、筛选、灯箱，桌面 + 移动端，全部按设计稿还原。本任务完成后 `python dev.py` 起的就是新前端。

## Requirements

### R1 目录切换
- `git mv frontend frontend-legacy`（纯改名提交，保住 rename 追踪），`frontend-legacy/README.md` 顶部加"已废弃，仅存档，不再维护"说明。
- 新 `frontend/` 从零搭建（Next.js 15 App Router + TS + Tailwind + TanStack Query），移植旧代码中仍适用的 `lib/api.ts`、`lib/types.ts`、hooks、`middleware.ts`、`components/ui/*` 模式。
- `dev.py` 不改（它指向 `frontend/`）；新前端沿用 `/api`、`/media` rewrite 代理。

### R2 设计令牌与基础
- `styles/globals.css` + `tailwind.config.ts` 落设计稿"Design Tokens"整表（背景/玻璃层/文字/强调渐变/分类色/评级色/圆角/动效曲线），页面内禁止散落硬编码色值。
- 字体：Noto Sans SC / Space Grotesk / JetBrains Mono 走 npm 包自托管（不依赖构建时访问 Google）；图标 lucide-react（按设计稿 README 的对照表）。
- 所有动效尊重 `prefers-reduced-motion`。

### R3 前台界面（桌面）
- **顶栏**：悬浮胶囊（56px，玻璃底 + blur），logo + 搜索胶囊（`/` 快捷键聚焦、空格=AND）+ 安全模式按钮（盾形，点击 PATCH `/me/settings`，成功后 refetch + Toast）+ 头像用户菜单（用户名区 + 退出登录；"管理面板/设置"入口在对应子任务完成前**不显示**）。
- **筛选栏**：240px 玻璃卡；区块＝已选条件 chips（可删）、标签（连带母子成组，数据来自 `GET /api/tags/tree`）、评级 S/Q/E 勾选（安全模式开时禁用）。无操作 8 秒自动折叠为 56px 图标条，悬停展开，图钉常驻（localStorage `rail_pinned`）；宽度动画 240↔56px / 220ms。选中条件序列化进 `?tags=` 与查询参数。
- **瀑布流**：贪心最短列算法，无限滚动（IntersectionObserver rootMargin 600px），新页卡片 fade-in-up 阶梯入场；卡片 radius 14，悬停底部渐变 + 评级 chip + id。
- **灯箱**：`?photoId=` URL 驱动浮层（打开 push、←→ 翻页 replace 用 `/next` 接口、Esc/遮罩/返回键 back 关闭、直达禁翻页单图取数）；左侧信息浮层：id + 评级 chip、下载/原图操作、作者区（artist 标签 chip + 该作者更多缩略图）、标签连带成组 chips、元数据 mono 行；两侧玻璃翻页钮 + 右上计数。
- **登录/初始化**：同壳玻璃卡，按设计稿样式，沿用现有接口与 `?next=` 跳转逻辑。

### R4 交互中间态
按 `final-states.dc.html`：加载骨架（shimmer 1.6s）、空图库（沿用现有文案 + 两个 CTA，CTA 在管理页存在前先指向说明）、筛选无结果（放宽建议）、加载失败（重试）、Toast（玻璃胶囊，sonner 自定义外观）。搜索联想下拉是子任务 2，本任务搜索框只做纯输入。

### R5 移动端（402 宽基准，响应式断点）
首页（搜索胶囊 + chips 行 + 双列瀑布流）、筛选抽屉（底部弹层，同筛选栏区块 + "应用筛选"）、灯箱（全屏、左右滑切换、下滑关闭、信息半层上拉）、登录。

### R6 后端配套
- `GET /api/posts` 增加评级多选参数（如 `ratings=safe,questionable`）：安全模式开 → 忽略参数强制 safe（服务端权威不变）；关 → 按参数过滤，缺省=全部。`lib/api.ts` 同步。

### 明确不做（本任务）
- 星标/收藏任何界面（父任务决策 3）。
- 搜索联想、作者筛选区、作者视图专属头部（子任务 2）。
- 管理面板全部页面（子任务 3-7）；用户菜单不出现其入口。
- 灯箱差分区（子任务 5）。
- 灯箱 ←→ 按当前筛选集翻页（沿用现有全局翻页语义，偏差记录在案）。

## Acceptance Criteria

- [ ] `git log --follow frontend-legacy/lib/api.ts` 能追到改名前历史；`frontend-legacy/README.md` 有废弃说明；`frontend-legacy/` 里 `npm run dev` 仍可手动启动。
- [ ] `python dev.py` 一键起新前端：初始化 → 登录 → 浏览 → 标签+评级筛选 → 灯箱翻页 → 登出，全流程可用（浏览器实测）。
- [ ] 评级参数 pytest：安全模式开时传 `ratings=explicit` 仍只返回 safe；关时按参数过滤；缺省返回全部评级。
- [ ] 新前端代码里搜不到星标/收藏相关 UI 与调用。
- [ ] 色值/圆角/字体只出现在令牌层（globals.css / tailwind.config.ts / ui 组件），页面组件内无硬编码十六进制色。
- [ ] 桌面 1280 与移动 402 两档视口截图对照 `.dc.html` 设计稿无明显偏差（布局、配色、圆角、留白）。
- [ ] `npm run lint`、`tsc --noEmit`、后端 `pytest` 全绿。
