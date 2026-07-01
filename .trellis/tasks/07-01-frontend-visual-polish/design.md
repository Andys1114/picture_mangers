# 前端视觉美化打磨 — 技术设计

> 需求见 `prd.md`。纯 Tailwind/CSS，零新依赖，不改功能契约。本文记 token/动效/组件改造决策。

## 1. 字体（next/font）

`app/layout.tsx` 顶部：
```ts
import { Inter, JetBrains_Mono } from "next/font/google";
const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });
```
`<html className={cn("dark", inter.variable, mono.variable)}>`。tailwind.config.ts `fontFamily.sans = ["var(--font-sans)", ...fallback]`、`mono = ["var(--font-mono)", ...]`。Mono 用于 md5 / 标签 chip / 计数等（`.font-mono`）。

> next/font 是内置零依赖；自动 self-host、swap、preload，无 CLS。

## 2. 新增 design token（globals.css）

```css
:root {
  /* 既有配色保留，增补： */
  --elevation-1: 0 1px 2px hsl(0 0% 0% / 0.4);           /* 卡片 */
  --elevation-2: 0 8px 30px hsl(0 0% 0% / 0.5);          /* 浮层/弹窗 */
  --ring: 217 91% 60%;                                    /* focus ring = accent */
  --shimmer-from: 240 5% 9%;
  --shimmer-to: 240 4% 14%;
}
```
Tailwind 扩展 `boxShadow`：`e1`/`e2`；`ringColor` 复用 accent。所有动效统一 token：`--dur-fast:150ms; --dur:200ms; --ease: cubic-bezier(0.22,1,0.36,1)`（ease-out）。

## 3. 组件改造

### 3.1 登录/向导页（login/setup）
- 背景：`<div class="fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,hsl(var(--accent)/0.12),transparent_55%)]" />`（accent 微光，不抢内容）。
- 顶部品牌：lucide `Images` 图标 + "PM Gallery" wordmark + tagline「个人图库」。
- 表单卡：`rounded-xl border border-border bg-surface/80 backdrop-blur shadow-e2 p-8`，宽度 max-w-sm。
- 输入聚焦：`focus-visible:ring-2 ring-accent`（已有，强化 ring-offset 透明）。
- 密码 show/hide：Input 右侧 `<button>` 切 `type`，lucide `Eye`/`EyeOff`，`aria-label`，spec `password-toggle`。
- 抽公共 `AuthCard` 组件复用 login/setup。

### 3.2 设置页（settings）
- 三段卡片：安全模式 / 账户（用户名）/ 关于。每段 `rounded-xl border bg-surface p-5 shadow-e1`，标题 + 描述 + 控件行。
- 账户段读 `useMe().username`；关于段放版本/说明。

### 3.3 顶栏（topbar）
- logo：`<Images className="h-5 w-5 text-accent" />` + wordmark。
- 底部分隔：`border-b border-border` 改 `after:` 渐变淡出（`bg-gradient-to-b from-border to-transparent`）。
- 滚动渐隐：transition 用 `--dur` + ease-out；hidden 用 `-translate-y-full opacity-0`（加 opacity 更顺）。
- 按钮：所有顶栏 icon button 加 `active:scale-95 transition`。

### 3.4 瀑布流卡片（post-card）
- 容器：`group relative mb-1 rounded-lg overflow-hidden bg-surface shadow-e1 transition duration-200 ease-out hover:scale-[1.02] hover:shadow-e2`（transform-only，无 reflow）。
- 图片：`<Image className="... opacity-0 transition-opacity duration-300"` + `onLoad` → `opacity-100`（淡入，防突兀）。`loading="lazy"` 保留。
- 底部渐变遮罩（替代纯黑）：`absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/70 to-transparent`，hover 时 `opacity-100`（默认 opacity-0）。遮罩内放分级 chip + ★。
- 分级 chip：`<span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] ${ratingColor(r).bg}/15 ${ratingColor(r).text}">` + lucide 小图标（Shield/ShieldAlert/ShieldX）——色+文+图标，`color-not-only`。
- ★ 按钮：`backdrop-blur rounded-full`，hover/focus 显现；**触屏可达**：`@media (hover: none)` 下默认 opacity-100（始终可见），见 §3.6。
- 卡片本身本期不可点（lightbox 是 #6）；保持。

### 3.5 瀑布流入场 stagger（masonry-grid）
- 每项 `animate-fade-in-up`，`animation-delay: calc(min(var(--i),6) * 40ms)`，`--i` 由 inline style 按 index 设。
- keyframes `fade-in-up`：`from { opacity:0; transform: translateY(8px) } to { opacity:1; transform:none }`，ease-out 200ms。
- `prefers-reduced-motion`：全局已有降级把 animation-duration 设 0.01ms，自动禁用 stagger（无需额外代码）。
- Skeleton shimmer：`bg-gradient-to-r from-[shimmer-from] via-[shimmer-to] to-[shimmer-from] bg-[length:200%_100%] animate-[shimmer_1.4s_infinite]`，keyframes `shimmer { to { background-position: -200% 0 } }`。
- 空态：lucide `ImageOff` 图标 + 文案（已有，加图标 + 间距）。
- 错误态：`isError` 时显示文案 + 「重试」按钮调 `refetch()`。

### 3.6 触屏 ★ 可达
globals.css：
```css
@media (hover: none) {
  .card-fav { opacity: 1 !important; }
}
```
post-card ★ 加 `card-fav` 类。这样无 hover 设备上 ★ 始终可见可点。

### 3.7 微交互统一
- Button 组件加 `active:scale-[0.97] transition-transform duration-150`（press 反馈，spec `press-feedback`/`scale-feedback`）。
- 全局 focus ring：`focus-visible:ring-2 ring-accent ring-offset-2 ring-offset-background`（已在 button/input，补到所有交互元素）。
- transitions 统一 `duration-200 ease-out`。

## 4. 不改的东西

- `lib/api.ts`/`lib/types.ts`/`lib/queryClient.ts`/`lib/colors.ts`：不改（colors 可能加 rating 图标映射，但签名不变）。
- hooks：不改。
- middleware / providers / 鉴权流：不改。
- 后端：完全不碰。
- shadcn ui 基元：button/input/skeleton 微调（press/focus/shimmer），不动 API。

## 5. 验证

- `npm run lint && npx tsc --noEmit && npm run build`。
- 手动：setup→login（看品牌+渐变+密码切换）→浏览（stagger 入场、卡片 hover、★ 触屏可见、skeleton shimmer、安全模式切换）→设置页（三段卡片）。
- 375px 不溢出；reduced-motion 开启看动效全降级；对比度 AA。
- 功能回归：无限滚动、安全模式过滤仍正常。
