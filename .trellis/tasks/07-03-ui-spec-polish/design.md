# 技术设计 — UI 规范优化

> 依据：`research/ui-audit-findings.md`（92 条确认发现，10 high / 28 medium / 54 low）。
> 原则：**只修不改设计**——保持深色沉浸 + 玻璃拟态视觉身份，全部为小的局部修改，集中一次提交，可 `git revert` 整体回滚。

## 分层实施顺序

自底向上改，避免上层改完又被底层牵动：

```
L1 Token 层     globals.css / tailwind.config.ts
L2 UI 基元层    ui/button, input, password-input, dropdown-menu, sheet
L3 业务组件层   browse/topbar, search-box, safe-mode-toggle, tag-drawer, post-card, masonry-grid
L4 页面层       (protected)/page, (protected)/layout, login, setup, settings(迁移)
L5 数据/文案层  hooks/useAuth, lib/colors 注释
```

## 关键技术决策

### D1 主色 --accent 调深一档（修 high #0：按钮白字 3.63:1）

`--accent: 217 91% 60%`(#3b82f6) → `221 83% 53%`(#2563eb)。复核员已实算全部影响面：

| 组合 | 旧 | 新 | 要求 |
|---|---|---|---|
| 白字 on accent（默认按钮） | 3.63:1 ✗ | **5.17:1 ✓** | ≥4.5 |
| accent 焦点环 on background | 5.44:1 | 3.83:1 ✓ | ≥3 |
| accent 图标 on bg-accent/15 | 3.14:1 | ≥3 ✓ | ≥3 |

副作用备忘：`tagCategoryColor` 的 `text-accent` 芯片文字会降到 2.98:1，但该函数**当前零调用点**，标签芯片接线（#7 切片）时改用 `text-blue-300` 类亮色变体即可——写入 spec 备忘，本次不动 colors.ts 逻辑。

### D2 destructive 按钮局部改底色（修 #0/#38）

`--explicit` 不动（它兼任错误文本色，5.26:1 达标）。`button.tsx` destructive 变体 `bg-explicit` → `bg-red-600`（白字 4.83:1 ✓），与 colors.ts 直接用 Tailwind 原色的既有惯例一致。

### D3 瀑布流 CSS columns → JS 分列 flex（修 high #7 追加页整列重排）

复核确认无纯 CSS 解法（column-fill:balance 每次追加都重新均衡所有列；grid masonry 未落地）。最小重构只动 `masonry-grid.tsx` + `globals.css`：

- 列数用 `matchMedia` 跟随现有断点（<768 → 2，<1024 → 3，<1280 → 4，else 5），SSR/首帧默认 4 列，仅断点变化时重排。
- 分配策略：**贪心入最短列**——用 `post.height/post.width` 累计各列估算高度（数据已有，无需测量 DOM）。追加新页只向列尾 push，**已渲染卡片永不移位**。
- 容器 `flex gap-1 items-start`，每列 `flex-1 min-w-0 flex flex-col`；卡片自带 `mb-1` 保持 4px 间距。
- 删除 `globals.css` 的 `.masonry` column-count 规则块。
- 附带修复同文件：IO 守卫 `isIntersecting && !isFetchingNextPage`（修 #28 重复触发）+ page.tsx 传稳定引用 `q.fetchNextPage`；stagger 改用**页内索引**（修 #75 追加页整块 240ms 延迟）。

### D4 评分角标对比度（修 #10/#14）+ 键盘可见（修 #11/12/17）

- 底色 `bg-black/40` → `bg-black/90`（复核实算白图最劣：safe 7.68 / questionable 9.12 / explicit 4.65，全达标；深图视觉几乎无差）。
- 角标 + 底部渐变加 `group-focus-within:opacity-100`，键盘 Tab 到卡片收藏钮时同样显现。
- `text-[11px]` → `text-xs`（回归 12px 下限与字号刻度，修 #48-50）。

### D5 顶栏滚动隐藏的键盘唤回（修 high #1-4，一处改动清四条）

隐藏分支追加 `focus-within:translate-y-0 focus-within:opacity-100`——Tailwind 变体选择器 (0,2,0) 特异性压过条件类 (0,1,0)，焦点在顶栏内的整个期间强制可见，无 JS。同文件顺手：`transition-all` → `transition-[transform,opacity]`（#40/42），logo aria-label 改为含可见文本的「PM Gallery 图库首页」（#39，Label-in-Name），用户名 `truncate` + `title` + 菜单 `max-w-[16rem]`（#41），退出项前加分隔线（#43）。

### D6 Sheet 补齐模态四件套（修 high #5/6 + #18/19/22/25/54 + 人工补充滚动锁）

约 25 行局部改动，全部在 `sheet.tsx`：

1. **焦点还原**：open effect 开头记 `document.activeElement`，cleanup 里 `.focus()` 归还。
2. **焦点圈闭**：Tab/Shift+Tab 在面板内可聚焦元素间循环；**空列表守卫**（当前抽屉为空态）→ `preventDefault()` 留焦点在面板。
3. **内置关闭钮**：面板右上角 X（lucide `X`，`aria-label="关闭"`），三种关闭方式齐全。
4. **滚动锁**：open 时 `document.body.style.overflow='hidden'`，cleanup 还原（人工补充项，批评员缺席补位）。
5. **动效语义**：面板加 `animate-slide-in-left`（新增 keyframe：translateX(-16px)+fade，200ms out-soft；right 侧对称），阴影 `shadow-xl` → `shadow-e2`。

### D7 DropdownMenu 补 menu 语义（修 #20/21/55/56/57）

- 打开时焦点移入首个 menuitem；`↑↓` 在条目间移动，`Esc`/选择后焦点还原到触发钮。
- `DropdownMenuItem` 加 `disabled:opacity-50 disabled:pointer-events-none` + `active:bg-surface/70`。
- 面板 `shadow-xl` → `shadow-e2`，进场 `animate-fade-in`（与全站出现语言一致）。

### D8 设置页迁入 (protected)（修 #27）

`app/settings/page.tsx` → `app/(protected)/settings/page.tsx`：URL 不变、MeGate/middleware 行为不变、顶栏自动获得。页内 `min-h-dvh` 改 `min-h-[calc(100dvh-3.5rem)]`（组布局已有 pt-14）。保留「返回图库」链接但箭头字符 `←` 换 lucide `ArrowLeft`（#69）。同步更新 `.trellis/spec/frontend/directory-structure.md` 的目录说明。

### D9 用户可见文案清理（修 #13/15/16/23/24/26/29-31/72，硬约束 8）

| 位置 | 现文案 | 新文案 |
|---|---|---|
| post-card toast | 已收藏（待 #8 接口） | 已收藏（云端同步开发中） |
| post-card toast | 已取消收藏（待 #8 接口） | 已取消收藏 |
| tag-drawer 空态 | 标签树数据待 #7 接入（GET /api/tags）… | 标签筛选即将上线：届时这里会按分类展示热门标签。 |
| masonry 空态副文案 | 导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。 | 导入本地文件夹或抓取 Danbooru 后，图片会出现在这里。 |
| settings 安全模式描述 | 开启后仅显示 safe 分级图片（后端按会话注入，默认开启）。 | 开启后仅显示分级为 safe 的图片（默认开启）。 |

### D10 全局零散（各一行）

- `globals.css` reduce 块补 `animation-delay: 0ms !important`（#36：否则 reduce 下卡片仍按 240ms 交错**延迟后瞬现**，且 both 填充模式下延迟期间不可见）。
- `html` 加 `scroll-padding-top: 4.5rem`（#37：Shift+Tab 聚焦滚动不再被 56px 固定顶栏遮住）。
- `Input` 焦点环补 `ring-offset-2 ring-offset-background`（#35/90），`PasswordInput` 改为**组合 `<Input className="pr-10">`** 消除双维护（人工补充项）。
- `tailwind.config.ts`：`fade-in` easing 统一为 out-soft（#89）；新增 `slide-in-left/right` keyframes（D6 用）。
- shimmer 改为 `::after` + `translateX` 合成器动画（#83），视觉不变。
- 手写按钮统一补四态：`active:scale-[0.97]`、`disabled:cursor-not-allowed`、`font-medium`、`ease-out-soft`（#32/46/55/59/65/67/77-81 等，涉及 safe-mode-toggle、tag-drawer 触发钮、post-card 收藏钮、password-input 眼睛钮）；settings 退出钮直接换用 `<Button variant="outline">` + pending 文案「退出中…」（#66/68/71）。
- `useLogout` 补 `onError: () => toast.error("退出失败，请重试")`（#33/34）。
- 装饰性 lucide 图标 sweep 补 `aria-hidden`（#73）。
- browse 页加 `sr-only` h1「图库」（#61）；settings 分区标题 `<p>` → `<h2>`（#64）。
- login/setup checking 态改为 AuthCard 同构居中骨架（#84/87）；登录兜底错误文案改「无法连接服务器，请确认后端已启动后重试」（#86）；setup 校验失败聚焦密码框 + `aria-invalid`（#88）；label 补 `font-medium`（#85）。
- 首页 Suspense fallback 复用骨架瀑布流组件（#62），骨架容器加 `role="status"` + sr-only「加载中」（人工补充）；主内容区与顶栏同宽 `max-w-[1800px] mx-auto`（#63）。
- 多行说明文字补 `leading-relaxed`（#60）；顶栏/设置用户名 truncate（#41/70）；`(protected)/layout` 去掉多余 `"use client"`（#91）；`colors.ts` 的 `ratingLabel` 注释改为与实现一致（人工补充）。

## 明确不做（记录在案）

- **列表虚拟化**（#74）：架构级，写入 spec 备忘，后续图片量上来再做。
- **被否决 5 条**（见 research 文末）：退出登录加确认框、sheet 玻璃拟态、tag-drawer 字重、colors.ts token 化、搜索清空按钮——复核员论证不成立或属项目既定惯例。
- **tagCategoryColor 的 text-accent 对比度**：零调用点，接线时处理（spec 备忘）。

## 验证与回滚

- 每层完成跑 `npx tsc --noEmit`；全部完成跑 `npm run lint` + 三档宽度（375/768/1440）目检 + 纯键盘走查（验收标准见 prd.md）。
- 单次提交；出问题 `git revert` 一把回滚，无迁移、无后端改动。
