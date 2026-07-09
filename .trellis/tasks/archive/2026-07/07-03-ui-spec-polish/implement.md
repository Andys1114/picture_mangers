# 执行清单 — UI 规范优化

> 按 design.md 的 L1→L5 分层顺序执行。每个工作包 = 一组文件的一次性改动；包间可独立验证。
> 全程不 commit（Phase 3 统一提交）。每层结束跑 `cd frontend && npx tsc --noEmit`。

## L1 Token 层

- [x] **W1 globals.css**：`--accent` → `221 83% 53%`；reduce 块补 `animation-delay: 0ms !important`；`html { scroll-padding-top: 4.5rem; }`；删除 `.masonry` 规则块（W8 接手）；shimmer 改 `::after` + translateX 合成器动画（视觉不变）。
- [x] **W2 tailwind.config.ts**：`fade-in` easing → `cubic-bezier(0.22,1,0.36,1)`；新增 `slide-in-left` / `slide-in-right` keyframes+animation（translateX(∓16px)+fade，200ms out-soft）。

## L2 UI 基元层

- [x] **W3 button.tsx**：destructive 变体 `bg-explicit hover:bg-explicit/90` → `bg-red-600 hover:bg-red-600/90`。
- [x] **W4 input.tsx + password-input.tsx**：Input 焦点环补 `ring-offset-2 ring-offset-background`；PasswordInput 重构为组合 `<Input type={show?"text":"password"} className="pr-10">`；眼睛钮 `rounded` → `rounded-md`、补 `active:scale-[0.97]`。
- [x] **W5 dropdown-menu.tsx**：打开聚焦首 item；↑↓ 移动焦点；Esc/选择后焦点还原触发钮；Item 补 `disabled:opacity-50 disabled:pointer-events-none active:bg-surface/70`；面板 `shadow-xl` → `shadow-e2` + `animate-fade-in`。
- [x] **W6 sheet.tsx**：记录并归还 opener 焦点；Tab 圈闭（空列表守卫）；内置右上角 X 关闭钮（`aria-label="关闭"`）；body 滚动锁（open→hidden，cleanup 还原）；面板 `animate-slide-in-left/right` + `shadow-xl` → `shadow-e2`。

## L3 业务组件层

- [x] **W7 topbar.tsx**：隐藏分支追加 `focus-within:translate-y-0 focus-within:opacity-100`；`transition-all` → `transition-[transform,opacity]`；logo `aria-label="PM Gallery 图库首页"`；用户名行 `truncate` + `title`、菜单 `max-w-[16rem]`；退出项前加 `<div className="my-1 border-t border-border" role="separator">`；图标补 `aria-hidden`。
- [x] **W8 masonry-grid.tsx（+page.tsx 传参）**：JS 分列 flex（matchMedia 断点 768/1024/1280→2/3/4/5 列，SSR 默认 4；贪心按 `height/width` 入最短列；追加只 push 列尾）；IO 守卫 `&& !isFetchingNextPage` 并补依赖；page.tsx 改传稳定引用 `q.fetchNextPage`；stagger 用页内索引 `Math.min(i % 40, 6) * 40`；空态文案去黑话（D9）；骨架容器 `role="status"` + sr-only「加载中」；抽出 `MasonrySkeleton` 供 W12 复用；`ImageOff` 补 `aria-hidden`。
- [x] **W9 post-card.tsx**：chip `bg-black/40` → `bg-black/90`、`text-[11px]` → `text-xs`；chip+渐变补 `group-focus-within:opacity-100`；收藏钮补 `cursor-pointer active:scale-[0.97]`、transition 收敛为 `transition-[opacity,background-color,transform] ease-out-soft`；卡片 transition 指定属性并统一 out-soft；toast 文案去黑话（D9）；alt 改「插画 {id} · 分级 {label}」；`Star` 补 `aria-hidden`。
- [x] **W10 safe-mode-toggle.tsx + tag-drawer.tsx + search-box.tsx**：
  - toggle：aria-label 固定「安全模式」+ aria-pressed 表状态；ON 态补 `hover:bg-safe/25`；补 `active:scale-[0.97] disabled:cursor-not-allowed font-medium ease-out-soft`；图标 `aria-hidden`。
  - drawer 触发钮：同款四态补齐；空态文案去黑话（D9）+ `leading-relaxed`；标题旁自然获得 Sheet 的 X 钮。
  - search-box：form 补 `min-w-0`（375px 不溢出）；`router.replace` → `router.push`（保留无查询时 replace 回 `/` 的分支也改 push，后退可回上一搜索）；用 `useEffect` 同步 URL `tags` 变化回输入框（后退/前进时不再显示旧词）。

## L4 页面层

- [x] **W11 settings 迁移**：`app/settings/page.tsx` → `app/(protected)/settings/page.tsx`；`min-h-dvh` → `min-h-[calc(100dvh-3.5rem)]`；分区标题 `<p>` → `<h2 className="font-medium">`；`←` → lucide `ArrowLeft`；退出钮换 `<Button variant="outline" className="text-explicit border-explicit/40 hover:bg-explicit/10">` + pending「退出中…」；用户名 truncate；安全模式描述去黑话（D9）；描述文字 `leading-relaxed`；图标 `aria-hidden`；同步改 `.trellis/spec/frontend/directory-structure.md`。
- [x] **W12 (protected)/page.tsx + layout.tsx**：页面加 `sr-only` h1「图库」；主内容区 `max-w-[1800px] mx-auto`；Suspense fallback 换 `MasonrySkeleton`；layout 去 `"use client"`。
- [x] **W13 login + setup + auth-card**：checking 态改 AuthCard 居中骨架（复用 Skeleton，`role="status"`）；login 兜底错误「无法连接服务器，请确认后端已启动后重试」；setup 校验失败 `passwordRef.focus()` + `aria-invalid`（login 同补 aria-invalid）；两页 label 补 `font-medium`；auth-card 图标 `aria-hidden`。

## L5 数据/文案层

- [x] **W14 useAuth.ts**：`useLogout` 补 `onError: () => toast.error("退出失败，请重试")`。
- [x] **W15 colors.ts**：`ratingLabel` 注释改为「Rating → 短标签（Danbooru 惯例 s/q/e）」。

## 质量检查（步骤 2.2，最后一轮全范围）

- [x] **V1** `cd frontend && npx tsc --noEmit` 零错误。
- [x] **V2** `cd frontend && npm run lint` 零错误。
- [x] **V3** 运行时冒烟（curl SSR）：/login 200 + checking 骨架（role=status）；未登录 / 与 /settings 均 307 → /login（中间件守卫）；登录 API 200；已认证 / 含 sr-only h1「图库」+ MasonrySkeleton + max-w-[1800px]；已认证 /settings 含顶栏 + 返回图库 + min-h-calc。**交互层走查（点击/键盘实际操作）由多智能体静态复核 + 回归猎手覆盖，建议真人再过一遍**。
- [x] **V4** 键盘路径经代码级复核确认：focus-within 唤回、Sheet 圈闭/还原、菜单方向键、卡片 group-focus-within（静态验证，同上建议真人复核）。
- [x] **V5** 375px 溢出根因（search-box min-w-0）已修并经复核确认；瀑布流前缀稳定分列经复核确认追加不移位。
- [x] **V6** reduce 覆盖（含 animation-delay 清零）经代码复核确认。
- [x] **V7** 逐条闭环：92 条 → 83 fixed + 1 recorded（virtualize-lists）+ 7 partial（已全部补修）+ 0 missed；回归猎手 6 条新问题已全部修复。明细见 `research/check-closure.md`。

### 检查阶段修正（相对 W 包规格的最终形态）

- W5 的 `disabled:pointer-events-none` 最终改为 `disabled:cursor-not-allowed`（pointer-events-none 会让点击穿透到菜单容器误关菜单）。
- W9 的卡片 transition 最终收敛为 `transition-transform`（阴影直接切换，不参与逐帧动画）。
- 新增修正：scrollbar-gutter: stable（抽屉滚动锁防跳动）、search-box 持焦不同步 + 同 URL 不压栈、masonry 列数惰性初始化、login/setup aria-invalid 按字段/错误类型限定、checking 骨架镜像表单结构、dropdown/tag-drawer/safe-mode/badge 过渡属性补全。

## 收尾（Phase 3）

- [x] spec 更新：`component-guidelines.md` 补「浮层阴影一律 e2」「手写按钮四态基线」「文案禁开发黑话」；备忘 tagCategoryColor 接线时的 text-accent 对比度与列表虚拟化。
- [x] 单次 commit：`fix(frontend): UI 规范打磨——按 92 条审计确认项修复（a11y/交互/动效/文案）`。

## 回滚点

任何 W 包出问题：该包文件 `git checkout --`；整体回滚：单 commit `git revert`。
