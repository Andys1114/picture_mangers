# 前端视觉美化打磨 — PRD

> 父任务：`06-28-gallery-app`。在已交付的 `06-30-frontend-skeleton-browse` 基础上做视觉/体验打磨。**不改任何功能契约**（API、类型、路由行为、鉴权流不变），仅视觉与微交互。技术设计见 `design.md`。

## 1. Goal / 用户价值

让现有深色沉浸画廊从「能跑的素版」升级到「有质感的专业版」：字体真正加载、登录/设置页有品牌感、顶栏更精致、瀑布流卡片 hover 更细腻、列表入场有节奏、加载/空态不突兀。所有打磨纯 Tailwind/CSS，零新依赖。

## 2. 已确认事实

- 前端栈：Next 15 + TS + Tailwind + shadcn 风格 UI + lucide + TanStack Query。已有 design token（globals.css CSS 变量：深色沉浸配色 + 分级色）。
- **字体未实际加载**：tailwind.config.ts 声明了 Inter / JetBrains Mono 字体栈，但没用 `next/font` 引入，实际回退到系统字体——这是当前最大的「不专业」来源。
- 当前各页面状态（刚交付）：
  - login/setup：扁平深色背景 + 居中表单卡，无品牌、无背景层次。
  - settings：近乎空壳，仅一个安全模式行 + 返回链接。
  - topbar：毛玻璃 + 滚动渐隐已实现，但 logo 纯文字、按钮态偏素。
  - post-card：hover 黑色遮罩 + ★ + 分级色条，较粗。
  - masonry：CSS columns，加载用 Skeleton（无 shimmer），无入场动效。
  - 全局：已有 `prefers-reduced-motion` 降级（保留）。
- spec 约束：图标 lucide（不切 Phosphor）；`<button>`/`<a>` 不用 `<div onClick>`；图片 alt+width/height；触控 ≥44px；无障碍对比度 AA。
- ui-ux-pro-max 搜索确认方向：Dark Mode OLED + Modern Dark Cinema（glassmorphism/glow/blur）适配画廊；ux 域强调 stagger 入场（30-50ms/项，封顶）、ease-out、skeleton shimmer、reduced-motion。

## 3. 范围

### In scope（纯 Tailwind/CSS，零新依赖）
- **字体加载**：`next/font/google` 引入 Inter（界面）+ JetBrains Mono（等宽，标签/md5 用），挂到 `<html>` / Mono 工具类。font-display swap 防 FOIT。
- **登录/向导页**：背景加微妙径向渐变（accent 微光）、品牌 wordmark + tagline、表单卡圆角/阴影/间距精修、输入聚焦态强化、密码可见切换（show/hide，spec `password-toggle`）。
- **设置页**：分 section 卡片结构（安全模式 / 账户 / 关于），视觉对齐其他页。
- **顶栏**：logo 加图标、按钮 hover/active 态、滚动渐隐曲线调顺、底部分隔线渐变。
- **瀑布流卡片**：hover 微缩放（scale 1.02，transform-only 不触发 reflow）、底部渐变遮罩替代纯黑、★ 按钮精修、分级色块改为带标签的小 chip（色+文，`color-not-only`）、图片 load 淡入。
- **瀑布流入场**：stagger 淡入上移（30-50ms/项，封顶 6 项后不再延后，reduced-motion 关闭）。
- **加载/空/错误态**：Skeleton shimmer（渐变扫描）、空态加图标 + 引导、查询错误态文案 + 重试按钮。
- **微交互**：按钮 press 缩放（0.97）、focus ring 统一、transitions 统一 ease-out 150-200ms。
- **触控**：卡片 ★ 在触屏（无 hover）上始终可见或点击卡片即显现，确保可操作。

### Out of scope
- framer-motion / 重动效 / 页面转场 spring（留后续，design.md 已规划给 #6 lightbox）。
- 任何后端 / API / 类型 / 路由行为改动。
- light 模式（本期仍 dark-only）。
- 新页面或新功能（lightbox、标签树、导入页等仍是 #6/#7/#8）。

## 4. 验收标准

- [ ] Inter + JetBrains Mono 经 `next/font` 真正加载，界面文字用 Inter，等宽处用 Mono；无 FOIT（swap）。
- [ ] 登录/向导页有背景层次（径向渐变）+ 品牌 wordmark + tagline；密码字段有 show/hide 切换。
- [ ] 设置页分 section 卡片，视觉与其他页一致。
- [ ] 顶栏 logo 含图标；按钮 hover/active 有反馈；滚动渐隐顺滑。
- [ ] 卡片 hover：微缩放 + 底部渐变遮罩 + ★ 精修 + 分级 chip（色+文）；图片 load 淡入。
- [ ] 瀑布流首屏 stagger 淡入（30-50ms/项，封顶），reduced-motion 下禁用。
- [ ] Skeleton 有 shimmer；空态有图标 + 引导；查询错误有重试按钮。
- [ ] 按钮统一 press 缩放 + focus ring；transitions 统一 ease-out。
- [ ] 触屏上 ★ 可操作（不依赖 hover）。
- [ ] `npm run lint` / `tsc --noEmit` / `npm run build` 干净；375px 不溢出；reduced-motion 降级；对比度 AA。
- [ ] 功能回归：setup→login→浏览→无限滚动→安全模式切换 全部仍正常。

## 5. 约束

- 零新运行时依赖（仅用 next/font 内置 + Tailwind/CSS）。
- 不改 `lib/api.ts`/`lib/types.ts`/hooks 契约；不动后端。
- 沿用现有 design token，可在 globals.css 增补 token（如 elevation、shimmer）但不换配色方向。
- 保留全局 `prefers-reduced-motion` 降级。
- 图标继续 lucide；UI 文本中文，代码标识符/注释英文。
