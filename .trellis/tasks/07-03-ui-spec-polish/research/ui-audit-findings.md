# UI 规范审计确认清单（多智能体审计 + 对抗复核）

> 工作流 wf_0c809910-b7e：10 维度审计员 -> 按文件对抗复核（复核员独立重算对比度/重读代码）。原始 98 条 -> 去重 97 -> 确认 92（high 10 / medium 28 / low 54）/ 否决 5。补漏批评员因 429 未跑，由人工通读补位（见 design.md 附加项）。

## frontend/app/(protected)/layout.tsx

### [LOW] spec-server-components (L1)

**问题**：纯静态壳层 layout 标了 "use client"，违反 component-guidelines「Server Components for static shells/layouts — no hooks, no interactivity」。

**证据**：L1 `"use client";`，组件体 L6-16 无任何 hook/事件处理，只渲染 `<Suspense>` + `<Topbar />`（Topbar 自身已是 client 组件，Suspense 在服务端组件可用）。

**修复**：删除 L1 的 `"use client";` 一行即可，其余不用动。

**复核**：Evidence 属实：L1 确为 "use client"; 组件体 L6-16 无任何 hook/事件处理/浏览器 API，只渲染 div + Suspense + Topbar + children。规则真实存在（.trellis/spec/frontend/component-guidelines.md L17：layout 等静态壳层应为 Server Component）。尝试推翻失败：(a) Suspense 在 Server Component 可用（Next 15.5/React 19）；(b) Topbar 自带 "use client"（topbar.tsx L1），server layout 引入 client 子组件是标准组合模式；(c) Suspense 边界是为 SearchBox 的 useSearchParams CSR bailout 而设，官方推荐写法恰是 server layout 提供边界，删指令后照常工作；(d) 根 layout 经 <Providers>{children}</Providers> 以 children-slot 组合，嵌套 server layout 无冲突。一行删除即可，属最小局部修改，severity low 恰当。

## frontend/app/(protected)/page.tsx

### [LOW] heading-hierarchy (L27)

**问题**：浏览主页整页没有 h1，页面上首个出现的标题反而是抽屉里的 h2「标签筛选」，标题层级从 h2 开始。

**证据**：(protected)/page.tsx L26-32 `<main className="pb-8">` 内只有 Suspense+BrowseView（瀑布流），topbar.tsx 全文件无任何 h 标签（logo 是 L46 的 Link/span）；tag-drawer.tsx L24 有 `<h2 className="font-medium">标签筛选</h2>`，成为该路由唯一且无 h1 前置的标题。

**修复**：在 (protected)/page.tsx 的 main 开头加 `<h1 className="sr-only">图库</h1>`（Tailwind 内置 sr-only，不影响视觉）。

**复核**：证据全部属实：page.tsx L27 <main className="pb-8"> 内仅 Suspense+BrowseView，无任何标题；topbar.tsx 全文无 h 标签（L46-55 是 Link/span logo）；tag-drawer.tsx L24 确有 <h2>标签筛选</h2>。全局 grep 证实 <h1> 只存在于 auth-card.tsx 和 settings/page.tsx，浏览主页整条路由树无 h1。补充核实：sheet.tsx L39 在关闭时返回 null，即抽屉关闭时页面连一个标题都没有，指控只轻不重。sr-only 是 Tailwind 内置工具类，fix 为一行局部修改，不动视觉，文案「图库」与 logo aria-label「图库首页」一致，severity low 恰当。

### [LOW] progressive-loading (L28)

**问题**：首页 Suspense fallback 只是左上角一行文字，SSR/水合前（JS 加载可远超 300ms）看不到骨架，水合后再跳成骨架瀑布流；纯 CSS shimmer 本可直接出现在 SSR HTML 里。

**证据**：app/(protected)/page.tsx L28：`<Suspense fallback={<div className="p-8 text-muted">加载中…</div>}>`；而真正的加载骨架在 masonry-grid.tsx L47-L54（12 个 `<Skeleton className="mb-1 w-full" style={{ height: 200 + (i % 4) * 60 }} />` 组成的 masonry 布局）只在水合后的 isLoading 分支出现。

**修复**：把 masonry-grid.tsx L47-55 的 isLoading 骨架块提取为同文件导出的 MasonrySkeleton 小组件（<div className="masonry p-1">{12 个 Skeleton}</div>），isLoading 分支与 page.tsx L28 的 Suspense fallback 都改用它：<Suspense fallback={<MasonrySkeleton />}>，首帧即骨架、水合无跳变。

**复核**：证据逐字属实：page.tsx L28 fallback 确为 <div className="p-8 text-muted">加载中…</div>；masonry-grid.tsx L47-55 确有 12 个 Skeleton（height: 200 + (i % 4) * 60）的 isLoading 骨架，仅在水合后出现。机制核实成立：BrowseView 在 Suspense 边界内调用 useSearchParams()，Next App Router 静态预渲染时会把该边界降级为客户端渲染并将 fallback 写入首屏 HTML，故水合前用户只见左上角一行文字，水合后跳成骨架瀑布流。Skeleton 的 shimmer 是纯 CSS（globals.css .shimmer + tailwind.config.ts shimmer keyframes），完全可在 SSR HTML 中直接生效。fix 是小的局部提取重构，无新依赖，且无论路由静态/动态都消除跳变，severity low 恰当。

### [LOW] container-width (L27)

**问题**：顶栏内容区上限 max-w-[1800px] 而画廊主内容区无最大宽度，≥1832px 视口（如 1920 常见桌面分辨率）时顶栏控件两侧内缩约 60px、网格却顶满全宽，跨区域不对齐

**证据**：topbar.tsx L45: <div className="h-full mx-auto max-w-[1800px] px-4 flex items-center gap-3">；对比 (protected)/page.tsx L27: <main className="pb-8"> 与 masonry-grid.tsx L82: <div className="masonry p-1">，两处均无 max-width，内容区与顶栏最大宽度不一致

**修复**：优先反向统一：删除 topbar.tsx L45 的 max-w-[1800px]（保留 mx-auto 可一并删）使顶栏与画廊同为全宽，保持沉浸式全出血身份且超宽屏无死边距；若产品上想要有界布局，替代方案才是给 page.tsx L27 的 main 加 mx-auto max-w-[1800px]。两者都是一行修改，二选一保持一致即可。

**复核**：三处引用逐字属实：topbar.tsx L45 有 mx-auto max-w-[1800px] px-4，page.tsx L27 的 main 与 masonry-grid.tsx L82 的 .masonry 均无最大宽度。数学复核成立：1920px 视口下 (1920−1800)/2=60px，顶栏控件两侧内缩约 60px 而网格顶满全宽，越宽越夸张（2560px 时达 380px/侧）。桌面优先里程碑下 1920/2560 属核心场景，不越界。唯一微瑕：不对齐严格从 >1800px 即开始而非 1832px，但不影响指控实质。fix 方向上，原 fix 首选「给 main 加 max-w-[1800px]」会在超宽屏给沉浸式画廊引入大片死边距，与深色沉浸式全宽瀑布流身份略冲突，故改写为优先删顶栏上限。

## frontend/app/layout.tsx

### [MEDIUM] fixed-element-offset (L28)

**问题**：html 未设置 scroll-padding-top，键盘 Shift+Tab 把视口上方的卡片滚入视图时元素贴视口顶部，而向上滚动恰好触发顶栏重新出现（z-40 fixed），焦点元素被 56px 顶栏遮住

**证据**：app/layout.tsx L28: <html lang="zh-CN" className={`dark ${inter.variable} ${mono.variable}`}>（无 scroll-pt）；顶栏 topbar.tsx L41: "fixed top-0 inset-x-0 z-40 h-14 ..."，且 L28 滚动逻辑 if (y < 8 || y < last) setHidden(false) 会在浏览器为聚焦元素向上滚动时立刻重新显示顶栏；(protected)/layout.tsx L9 的 <div className="pt-14"> 只解决静态排版偏移，不影响 scrollIntoView 定位。键盘可达性是项目一级要求（约束 6）

**修复**：在 app/layout.tsx L28 的 html className 加 scroll-pt-14（即 `dark scroll-pt-14 ...`），或在 globals.css @layer base 的 html 规则里加 scroll-padding-top: 3.5rem，与 h-14 顶栏等高，使 focus/锚点滚动定位到顶栏下方

**复核**：全部证据属实：layout.tsx L28 的 html 无任何 scroll-pt 类，全 frontend 无 scroll-padding/scroll-margin（grep 零命中），globals.css 的 html 规则只有 color-scheme。topbar.tsx L41 确为 fixed top-0 z-40 h-14，L28 的 if (y < 8 || y < last) setHidden(false) 保证浏览器为聚焦元素向上滚动时顶栏必然重现。页面为 window 级滚动（body min-h-dvh，浏览树无内部 overflow 容器，topbar 监听 window.scrollY），因此 html 上的 scroll-padding-top 正是生效位置。机制比指控更严重：post-card.tsx L70 每张卡片有真实 <button>（收藏★，top-2 h-9），Shift+Tab 时浏览器最小滚动把该按钮顶边对齐视口 y=0，整个 36px 控件连同 focus ring 全部落在 56px 顶栏之下；bg-background/70 + backdrop-blur-md 使其成为不可读的模糊残影，违反 WCAG 2.2 SC 2.4.11（Focus Not Obscured）。键盘可达性为项目一级硬性要求（约束 6），在范围内。fix 为单类/单行局部修改且与现有 pt-14/h-14 的 56px 约定一致，scroll-pt-14 是 Tailwind v3 核心工具类，无需改写。

## frontend/app/login/page.tsx

### [LOW] content-jumping (L44)

**问题**：登录页 checking 态是左上角一行文本，auth/status 返回后整页跳变为全屏居中的 AuthCard，布局跳动明显。

**证据**：login/page.tsx L44：`if (checking) return <div className="p-8 text-muted">加载中…</div>;`，而最终渲染的 AuthCard 外层是 `min-h-dvh flex flex-col items-center justify-center`（auth-card.tsx L16）。

**修复**：login/page.tsx L44 与 setup/page.tsx L48（两处代码完全相同）的占位统一改为与 AuthCard 外壳同构：`if (checking) return <main className="min-h-dvh flex items-center justify-center p-8 text-sm text-muted">加载中…</main>;`，使完成后仅内容变化、位置不跳（text-sm 与项目内 muted 辅助文字规格一致）。

**复核**：证据逐字属实：login/page.tsx L44 正是 `if (checking) return <div className="p-8 text-muted">加载中…</div>;`，auth-card.tsx L16 外壳为 `min-h-dvh flex flex-col items-center justify-center`。尝试推翻失败：app/layout.tsx 的 body 只有 `min-h-dvh bg-background text-foreground antialiased`、无任何居中，checking 占位确实渲染在左上角，auth/status 返回后整页跳为全屏居中卡片，且每次访问 /login 都会经历这个跳变。不越界：桌面渲染问题、非新功能、修复仅改一行 Tailwind 类。severity low 恰当（纯视觉稳定性、通常不到一秒）。注意 setup/page.tsx L48 有一模一样的占位，原 fix 漏掉了。

### [LOW] weight-hierarchy (L50)

**问题**：登录/初始化表单的 label 只有 text-sm、字重 400，与旁边的说明文字无字重区分，不符合标签 500 的层级（shadcn Label 惯例为 font-medium）

**证据**：login/page.tsx L50: <label htmlFor="u" className="text-sm">用户名</label>、L60 同；setup/page.tsx L54、L64-67 同（其中 L66 的辅助文字「至少 8 位」也是嵌在 label 内，与主标签无字重差）

**修复**：四处 label 的 className 由 "text-sm" 改为 "text-sm font-medium"（login/page.tsx L50、L60；setup/page.tsx L54、L64）；同时 setup/page.tsx L66 嵌在 label 内的辅助 span 补上 font-normal，改为 `<span className="text-muted ml-1 text-xs font-normal">至少 8 位</span>`，否则它会继承父级的 500 字重，说明文字无法保持 400。

**复核**：证据逐字属实（login L50/L60、setup L54/L64-67 均为 `className="text-sm"` 的裸 label）。尝试用现有组件推翻失败：项目 components/ui/ 下没有 label.tsx（只有 input/button/badge 等），Input 组件也不给 label 施加任何字重，所以指控未被现有代码满足。规则真实存在（.claude/skills/ui-ux-pro-max/SKILL.md L168：Medium labels 500），且项目自身惯例支持——settings 页 SectionCard 标题用 font-medium + text-muted 说明、button/badge 均 font-medium，shadcn Label 标准实现也是 `text-sm font-medium`。加一个字重类不属于重设计、不换字体。severity low 恰当。但原 fix 有缺陷：setup L66 的「至少 8 位」span 嵌在 label 内且无字重类，label 加 font-medium 后该 span 会继承 500，与 fix 自称的「说明文字保持 400」矛盾，需补 font-normal。

### [LOW] error-clarity (L38)

**问题**：非 ApiError（如后端未启动、网络断开时 fetch 抛 TypeError）的兜底错误只有「登录失败」两个词，没有原因和补救动作（setup 页 42 行的「创建失败」同样问题）。

**证据**：login/page.tsx L38: setError(err instanceof ApiError ? err.message : "登录失败");（后端 ApiError 路径返回中文明确消息如「用户名或密码错误」，仅兜底文案裸露）

**修复**：兜底文案改为「登录失败：无法连接服务器，请确认服务已启动后重试」；frontend/app/setup/page.tsx 第 42 行的「创建失败」同样改为「创建失败：无法连接服务器，请稍后重试」。

**复核**：证据逐字属实（login L38、setup L42）。技术路径经 lib/api.ts 复核成立：request() 仅在 `!res.ok` 时抛 ApiError（HTTP 错误都会带上后端中文消息或「请求失败 (status)」兜底），而 fetch 本身被拒（后端未启动/断网）抛的是原生 TypeError，不经任何包装直达 onError，`err instanceof ApiError` 为 false → 裸「登录失败」/「创建失败」。即兜底文案暴露的场景恰好就是最需要解释原因的「连不上服务器」场景，无原因、无补救动作，error-clarity 违规成立。修复文案为简体中文、无工单号/接口名等黑话（符合约束 8），两行局部字符串修改，属 PRD R4 文案清理范畴，不越任何硬约束。severity low 保留：该路径仅在服务不可达时触发（dev.py 一键启动流程下相对少见），不影响正常登录反馈（ApiError 路径已有明确中文消息）。fix 最小且合适，无需改写；若后续想一处管全局，可在 lib/api.ts 的 request() 里把网络层异常统一包成带该消息的 ApiError，但那超出本条的最小修改要求。

## frontend/app/settings/page.tsx

### [MEDIUM] persistent-nav (L42)

**问题**：设置页在 (protected) 路由组之外，受保护页面间顶栏不一致：进入 /settings 后玻璃拟态顶栏（Logo、搜索、标签、账户菜单）整体消失，只剩文字返回链接。

**证据**：文件位于 frontend/app/settings/page.tsx（不在 app/(protected)/ 组内），settings/page.tsx:42 `<main className="relative min-h-dvh p-6">` 自带整页布局；而顶栏只在组布局渲染：app/(protected)/layout.tsx:9-13 `<div className="pt-14"><Suspense fallback={null}><Topbar /></Suspense>{children}</div>`。MeGate（providers.tsx:26）已把 /settings 视为受保护路由。

**修复**：把 frontend/app/settings/page.tsx 移到 frontend/app/(protected)/settings/page.tsx（URL 不变，MeGate/middleware 行为不变），保留页内「返回图库」链接；随手两处收尾：L42 的 min-h-dvh 在组布局 pt-14 下会多出 56px 滚动，可改为去掉 min-h-dvh 或 min-h-[calc(100dvh-3.5rem)]；同步更新 .trellis/spec/frontend/directory-structure.md L26 的目录位置。

**复核**：All three evidence points verified: file sits outside app/(protected)/; Topbar renders only in (protected)/layout.tsx; MeGate (providers.tsx:26) and frontend/middleware.ts (PUBLIC=[/login,/setup]) both already treat /settings as protected, and the topbar account menu itself links to /settings — so following that link makes the persistent glass topbar vanish. Not a new feature (page and topbar both exist); the fix is a URL-preserving file move, a small refactor not architecture-level. medium is appropriate for a nav-consistency break. Note: directory-structure.md L26 currently lists settings outside the group, but that doc is a descriptive layout snapshot, not a prohibition.

### [LOW] heading-hierarchy (L28)

**问题**：设置页三个分区标题「安全模式/账户/关于」用的是 <p>，页面只有孤立的 h1，读屏用户无法按标题跳转到各设置分区。

**证据**：settings/page.tsx L28 `<p className="font-medium">{title}</p>`（SectionCard 标题），L21 外层是语义化 `<section>` 却无标题元素；L49 `<h1 className="text-xl font-semibold">设置</h1>` 之下再无任何 h2。

**修复**：把 L28 的 `<p className="font-medium">` 改为 `<h2 className="font-medium">`（字号样式已由类名控制，视觉不变，形成 h1→h2 层级）。

**复核**：Evidence exact: L28 is <p className="font-medium">{title}</p> inside a <section> with no heading; only heading in file is the L49 h1. No aria-labelledby anywhere. Screen-reader section navigation is a11y (first-class per constraints). Fix is safe: Tailwind preflight resets heading font-size/weight to inherit, so h2 with the same class is visually identical.

### [LOW] cursor-pointer (L72)

**问题**：设置页退出登录按钮禁用时仍显示手型光标：有 cursor-pointer + disabled:opacity-50，缺禁用态光标降级。

**证据**：L72: `"inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm text-explicit border border-explicit/40 hover:bg-explicit/10 transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"` — 无 disabled:cursor-not-allowed。

**修复**：加 `disabled:pointer-events-none`（与 ui/button.tsx L6 基线一致，同时消除禁用态 hover 背景）；若采纳 index 8 的 Button 重构则本条自动解决。

**复核**：L72 class string matches exactly: cursor-pointer + disabled:opacity-50, no disabled cursor degradation, and disabled state is reachable (logout.isPending, and !me.data during initial load). CSS cursor:pointer still applies to disabled buttons. However the proposed class is not the project convention — ui/button.tsx baseline uses disabled:pointer-events-none, which also suppresses the hover tint.

### [LOW] loading-buttons (L76)

**问题**：退出登录是异步请求，pending 时只 disabled+降透明度，没有加载指示；同项目的登录/创建按钮都有“登录中…/创建中…”文案切换，这里不一致。

**证据**：L70-76: `disabled={logout.isPending || !me.data}` … 按钮文本固定为 `退出登录`；对比 login/page.tsx L71 `{login.isPending ? "登录中…" : "登录"}`。

**修复**：按钮文案改为 `{logout.isPending ? "退出中…" : "退出登录"}`（沿用项目现有的文案切换惯例）。

**复核**：Evidence exact: L71 disabled={logout.isPending || !me.data} with fixed text 退出登录; login/page.tsx L71 has {login.isPending ? "登录中…" : "登录"} and setup/page.tsx L80 has 创建中…, so the pending-text convention is established project-wide and this button breaks it. Fix is the minimal convention-following text swap.

### [LOW] press-feedback (L72)

**问题**：设置页退出登录按钮无按下反馈（无 active: 态）。

**证据**：L72 类名含 `hover:bg-explicit/10 transition cursor-pointer …` 但无 active:*。

**修复**：类名加 `active:scale-[0.97]`，与 ui/button.tsx 基线一致。

**复核**：L72 has hover: and transition but no active: state; verified ui/button.tsx cva base includes active:scale-[0.97], so the proposed class matches the project baseline exactly (and reduced-motion handling in globals.css is unaffected — it only zeroes transition duration). Subsumed automatically if index 8's Button refactor is applied.

### [LOW] consistency (L72)

**问题**：设置页退出登录按钮高度 h-9 脱离按钮尺寸体系（Button 只有 h-8/h-10/h-11），且与上一张卡片同列的 SafeModeToggle（h-10）差 4px。

**证据**：settings/page.tsx:72 `className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm text-explicit border border-explicit/40 ..."`

**修复**：把 `h-9` 改为 `h-10`，与 SafeModeToggle（safe-mode-toggle.tsx:38 h-10 px-3）及 Button 默认尺寸对齐。

**复核**：Verified: L72 has h-9 px-3; Button size scale is h-8/h-10/h-11 only (button.tsx L17-22); safe-mode-toggle.tsx L38 is h-10 px-3 and renders in the visually parallel right slot of the card directly above, so the 4px mismatch is real. h-9→h-10 is minimal; index 8's Button swap (default size h-10) resolves this identically.

### [LOW] no-emoji-icons (L51)

**问题**：「返回图库」链接用文本箭头字符「←」充当图标，而非项目统一的 lucide-react SVG。

**证据**：settings/page.tsx:51 `← 返回图库`（Link 内为纯文本箭头字符）

**修复**：从 lucide-react 引入 ArrowLeft（该文件已 import lucide），Link 加 `inline-flex items-center gap-1`，内容改为 `<ArrowLeft className="h-4 w-4" /> 返回图库`。

**复核**：L51 is the literal text arrow ← inside the Link; the project icon system is lucide-react (hard constraint 4) and this very file already imports 4 lucide icons, so a text glyph as a nav icon is a genuine inconsistency. Fix (ArrowLeft + inline-flex items-center gap-1 on the Link) is minimal and keeps existing text-sm text-muted hover classes.

### [LOW] truncation-strategy (L66)

**问题**：设置页「当前用户：{username}」渲染在无换行防御的 flex 子项里，超长无空格用户名（flex min-width:auto）会横向溢出卡片圆角边界

**证据**：L66: description={me.data ? `当前用户：${me.data.username}` : "未登录"}，渲染处 L29: <p className="text-sm text-muted mt-0.5">{description}</p>；外层 L22-27 两层 flex（"flex items-start justify-between gap-4" / "flex items-start gap-3"）均无 min-w-0，长 token 不会收缩换行

**修复**：L23 内层 flex div 与 L27 文本 div 各补 min-w-0，L29 的 p 补 break-words；正常中文描述不受影响，超长用户名在容器边界折行不溢出

**复核**：Evidence exact (L66, L29, L22-27 flex chain with no min-w-0, right slot is shrink-0, section has no overflow clipping). Reachability verified against backend: username max_length=64 (schemas/auth.py:8) with no charset restriction; a 64-char unbroken or CJK name (~500-900px) exceeds the ~460px available in the max-w-2xl card, so flex min-width:auto overflow past the rounded border is real. min-w-0 on both flex items + break-words is the correct minimal chain (break-words alone would not work without min-w-0).

### [LOW] spec-token-styling (L72)

**问题**：退出登录按钮手写复刻了 shadcn Button 的全套基础样式，且高度 h-9 不在设计系统尺寸档（Button 只有 h-8/h-10/h-11），绕开源码自有的 Button primitive，属「逐处重涂」。

**证据**：L72 `className="inline-flex items-center gap-1.5 h-9 px-3 rounded-md text-sm text-explicit border border-explicit/40 hover:bg-explicit/10 transition cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"` — 与 button.tsx L6 cva 基类大段重复。

**修复**：改用 `<Button variant="outline" className="text-explicit border-explicit/40 hover:bg-explicit/10" onClick={...} disabled={...}>`，语义色通过 className 覆盖即可，尺寸回归 h-10 标准档。

**复核**：L72 duplicates most of the button.tsx L6 cva base (inline-flex/rounded-md/text-sm/transition/cursor-pointer/focus-visible ring/disabled:opacity-50) while drifting from it (no active state, no disabled:pointer-events-none, no ring-offset, off-scale h-9). Fix viability verified: cn() uses twMerge (lib/utils.ts), so text-explicit/border-explicit\/40/hover:bg-explicit\/10 reliably override the outline variant's text-foreground/border-border/hover:bg-surface; only an added Button import is needed. Applying this fix also resolves indexes 1, 3, and 4 in one move.

### [LOW] spec-no-dev-jargon (L58)

**问题**：安全模式的设置项描述含「后端按会话注入」这类实现机制黑话，普通用户不可理解。

**证据**：L58 `description="开启后仅显示 safe 分级图片（后端按会话注入，默认开启）。"`

**修复**：改为用户视角描述：「开启后仅显示 safe 分级图片（每次登录默认开启）。」

**复核**：L58 evidence exact; 「后端按会话注入」 is implementation jargon in user-visible copy, banned by the project's own constraint (R4/硬约束8). The replacement copy was fact-checked against the backend and is accurate: safe_mode lives on the Session row and every new session defaults to True (services/auth.py:45, tests/test_posts.py:186), so 「每次登录默认开启」 is truthful, minimal, and user-facing.

## frontend/app/setup/page.tsx

### [LOW] content-jumping (L48)

**问题**：初始化页 checking 态与登录页同样是左上角一行文本，校验完成后跳变为全屏居中卡片。

**证据**：setup/page.tsx L48：`if (checking) return <div className="p-8 text-muted">加载中…</div>;`，最终布局为 AuthCard 的 `min-h-dvh flex flex-col items-center justify-center`（auth-card.tsx L16）。

**修复**：setup L48 改为 `return <main className="min-h-dvh flex items-center justify-center p-8 text-muted">加载中…</main>;`，使占位与 AuthCard 最终居中位置一致；login/page.tsx L44 是完全相同的一行，应一并做同样修改（原 fix 中「与登录页同样处理」表述会让人误以为 login 已是正确写法）。

**复核**：Evidence 逐字符合：setup/page.tsx L48 正是 `if (checking) return <div className="p-8 text-muted">加载中…</div>;`，auth-card.tsx L16 正是 `min-h-dvh flex flex-col items-center justify-center`。试图推翻的两条路都不成立：(1) 根 layout 的 body 只有 `min-h-dvh bg-background text-foreground antialiased`，无居中；app 下仅有根 layout 和 (protected)/layout.tsx，/setup 不在 (protected) 内，无嵌套 layout 兜底居中；(2) checking 初始为 true 且 api.status() 为异步网络请求，占位必然渲染至少一帧，跳变真实可见。桌面同样受影响，非移动/浅色问题，fix 是纯 Tailwind 类局部小改，符合约束。severity low 恰当。唯一问题是 fix 表述：「与登录页同样处理」有误导——login/page.tsx L44 有一模一样的左上角占位，它不是正确范本而是同病灶。

### [LOW] focus-management (L35)

**问题**：提交失败后焦点不回到出错字段：setup 的「密码至少 8 位」校验失败后焦点留在提交按钮，密码框也没有 aria-invalid（login 页 38 行认证失败同样不聚焦任何字段），键盘用户需手动 Shift+Tab 回去改。

**证据**：setup/page.tsx L34-37: if (password.length < 8) { setError("密码至少 8 位"); return; } — 无 ref.focus()、无 aria-invalid；login/page.tsx L37-39 onError 仅 setError

**修复**：保留原方案主体：setup 加 `const passwordRef = useRef<HTMLInputElement>(null)` 传给 PasswordInput，长度校验失败分支加 `passwordRef.current?.focus()`；login 在 onError 里聚焦用户名输入。但 aria-invalid 不要绑 `!!error`（error 也可能是与密码无关的服务端「创建失败」）：另设 `const [pwdInvalid, setPwdInvalid] = useState(false)`，长度校验失败时置 true 并 focus，onSubmit 开头与密码 onChange 时清为 false，密码框上 `aria-invalid={pwdInvalid || undefined}`。仍是局部小改。

**复核**：Evidence 逐字符合：setup/page.tsx L34-37 为 `if (password.length < 8) { setError("密码至少 8 位"); return; }`，login/page.tsx L37-39 onError 仅 setError。全 frontend grep 证实：无任何 aria-invalid，唯一 .focus() 在 sheet.tsx（抽屉焦点管理），页面与 Input/PasswordInput 组件内部均无错误后聚焦逻辑，指控未被现有代码满足。无法用原生校验推翻：输入框虽有 required，但 1-7 位密码能通过 required 进入自定义分支，此时若经点击/在按钮上回车提交，焦点停在提交按钮属实。role="alert" 只解决读屏播报不解决键盘焦点，发现自己也承认了这点。键盘可达性是硬性 first-class 要求（约束 6），不受桌面优先豁免，在范围内。PasswordInput 已是 forwardRef 直通内部 input（password-input.tsx L9-24），fix 无需改组件、确属局部小改。severity low 恰当（流程仍可完成、错误有播报，属最佳实践补强）。小瑕疵：`aria-invalid={!!error}` 会在服务端错误（如「创建失败」）时误标密码框。

## frontend/components/browse/masonry-grid.tsx

### [HIGH] content-jumping (L82)

**问题**：瀑布流用 CSS 多列（column-count）实现，无限滚动每次追加下一页都会触发整列重新均衡，已在视口内的卡片跨列/纵向大幅移位。

**证据**：masonry-grid.tsx L82-L91：`<div className="masonry p-1">` 内 `{flat.map((post, i) => (`，新页数据直接追加到同一容器；globals.css L56-L74：`.masonry { column-gap: 4px; column-count: 2; }` 及 768/1024/1280 断点下 `column-count: 3/4/5`。CSS 多列容器高度为 auto 时默认 column-fill: balance，追加子元素会重新分配全部内容。

**修复**：组件内小重构（只动 masonry-grid.tsx + globals.css）：把 `flat` 按 `i % colCount` 拆成列数组，容器改 `flex gap-1 items-start`、每列 `flex-1 flex flex-col`（保持 4px 间距，卡片自带 mb-1），colCount 用 matchMedia 跟随现有 768/1024/1280 断点（SSR 默认 4 列）；删除 globals.css 的 .masonry column-count 规则。追加新页时只向各列尾部 push，已有卡片位置不再变化。

**复核**：证据属实：masonry-grid.tsx L82-91 单容器 flat.map 追加渲染，globals.css L55-77 为 column-count 2/3/4/5 多列布局。技术机理成立：多列容器高度 auto 时 column-fill 默认 balance，追加 40 张卡会重新划分所有列的内容边界——多列布局按序竖向灌列，除第一列开头外几乎全部卡片会跨列+纵向移位，用户视口横跨 2-5 列的那条可视带每翻一页都大幅跳动；post-card 的显式 width/height 只防图片加载抖动，防不了追加重排，break-inside:avoid 只防单卡截断。无纯 CSS 解法（column-fill:auto 需定高、grid masonry 未落地），JS 拆列是业界标准最小方案；fix 只动本组件+globals.css，gap-1/mb-1 恰为现有 4px 间距，符合约束 7 的"小重构"。核心浏览面每页必现的视觉跳动，high 恰当。

### [MEDIUM] fetch-dedup (L39)

**问题**：fetchNextPage prop 每次渲染都是新函数，effect 依赖它导致 IntersectionObserver 每次渲染重建，新 observer 的初始回调在请求进行中会再次触发 fetchNextPage（v5 默认 cancelRefetch:true → 取消并重发请求）。

**证据**：masonry-grid.tsx L37-L45：`const io = new IntersectionObserver((entries) => { if (entries[0].isIntersecting) fetchNextPage(); }, { rootMargin: "600px 0px" });` 依赖数组 `}, [hasNextPage, fetchNextPage]);`（L45）；app/(protected)/page.tsx L19：`fetchNextPage={() => q.fetchNextPage()}`（每次渲染产生新引用）。触发翻页后 isFetchingNextPage 翻转引起重渲染 → effect 重建 IO → IO 对已 observe 的元素立即派发初始回调，此时哨兵仍在 600px rootMargin 内。

**修复**：masonry-grid.tsx 回调加守卫：`if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();` 并把 isFetchingNextPage 加入依赖数组；（可选加固）page.tsx 直接传稳定引用 `fetchNextPage={q.fetchNextPage}`。

**复核**：证据属实：page.tsx L19 内联箭头函数每渲染新引用、masonry-grid.tsx L45 依赖数组含 fetchNextPage、@tanstack/react-query ^5.62（v5 fetchNextPage 默认 cancelRefetch:true）。链路成立：触发翻页→isFetchingNextPage 翻转→BrowseView 重渲染→新 prop 引用→effect 重建 IO；IntersectionObserver 规范保证 observe 后必派发一次初始回调，此刻新页未到、哨兵仍在 600px rootMargin 内，isIntersecting=true 再触发 fetchNextPage→取消并重发在途请求，且重发引起的状态更新可再次循环。MasonryGrid 无 memo、无守卫，无现有机制拦截。守卫 !isFetchingNextPage + 补依赖是 react-query 官方惯用写法，最小修改；传稳定引用 q.fetchNextPage（v5 函数引用稳定）作加固也正确。medium 恰当。

### [MEDIUM] consistency (L75)

**问题**：空状态文案对用户暴露工单号「（待 #8）」，属开发内部黑话，违反硬约束 8。

**证据**：masonry-grid.tsx:75 `<p className="text-sm">导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。</p>`

**修复**：删除「（待 #8）」，改为「导入本地文件夹或抓取 Danbooru 后，图片会出现在这里。」

**复核**：L75 逐字属实：「导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。」其中「#8」为工单号，直接违反硬约束 8（用户可见文案禁开发黑话）。fix 为删词改句，最小且文案通顺。注意：index 4/6/7 是同一缺陷经三条规则重复上报，落地合并为一次修改即可；另 post-card.tsx L31 的 toast「已收藏（待 #8 接口）」是同类问题（不在本条证据内，建议顺手一并清理）。

### [MEDIUM] empty-states (L75)

**问题**：图库空态引导文案末尾带工单号「（待 #8）」，内部黑话出现在用户可见文案里。

**证据**：masonry-grid.tsx L75: <p className="text-sm">导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。</p>

**修复**：删除「（待 #8）」，保留引导：「导入本地文件夹或抓取 Danbooru 后，图片会出现在这里。」（导入入口属后续切片，本次不要求加按钮。）

**复核**：与 index 4 为同一缺陷（empty-states 规则视角），L75 证据逐字属实，违反硬约束 8。fix 合理且明确声明不加导入按钮，正确避开了约束 5（导入入口属后续切片）。落地时与 index 4/7 合并为一次修改。

### [MEDIUM] spec-no-dev-jargon (L75)

**问题**：空状态文案末尾带工单号「（待 #8）」，属用户可见的开发内部黑话。

**证据**：L75 `<p className="text-sm">导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。</p>`

**修复**：删除「（待 #8）」：「导入本地文件夹或抓取 Danbooru 后，图片会出现在这里。」

**复核**：与 index 4/6 为同一缺陷（spec-no-dev-jargon 维度），L75 证据逐字属实，「#8」即约束 8 明文禁止的工单号。fix 文本与另两条一致，合并执行一次即覆盖三条。

### [LOW] alt-text (L60)

**问题**：多处纯装饰 lucide 图标没加 aria-hidden（lucide-react 0.468 默认不带），装饰性 SVG 暴露在无障碍树里产生读屏噪音。

**证据**：masonry-grid.tsx L60 与 L73 `<ImageOff className="h-8 w-8" />`（错误/空状态装饰图）、auth-card.tsx L26 `<Images className="h-5 w-5" />`（品牌图标）、settings/page.tsx L25 `<Icon className="h-4 w-4" />`（分区图标）均无 aria-hidden；已核实 node_modules/lucide-react/dist/cjs/lucide-react.js 的 defaultAttributes 不含 aria-hidden。项目已有正确示范：search-box.tsx L29 的 Search 图标显式写了 `aria-hidden`。

**修复**：给上述四处独立装饰图标补 `aria-hidden` 属性（与 search-box.tsx 的现有写法一致；按钮内已被 aria-label 覆盖的图标可不动）。

**复核**：四处代码逐一核实逐字存在且均无 aria-hidden（masonry-grid.tsx L60/L73、auth-card.tsx L26、settings/page.tsx L25）；实测 node_modules/lucide-react/dist/cjs/lucide-react.js L17-27 的 defaultAttributes 确不含 aria-hidden，组件经 ...rest 支持透传该属性；search-box.tsx L27-30 确已树立 aria-hidden 惯例。四处图标均为紧邻文字的纯装饰图标（ImageOff 旁有说明文字、Images 旁有品牌字、SectionCard 图标旁有标题），加属性是最小改动且合项目惯例。post-card 内 Star 按钮已有 aria-label 覆盖、finding 已正确排除。severity low 恰当。

### [LOW] virtualize-lists (L69)

**问题**：无限滚动的所有已加载卡片永久驻留 DOM（无窗口化、无 maxPages 截断），深滚动后节点与图片内存持续累积（架构级，仅记录）。

**证据**：masonry-grid.tsx L69：`const flat = pages.flat();`，L83：`{flat.map((post, i) => (` 全量渲染；hooks/useInfinitePosts.ts L12-L21 的 useInfiniteQuery 未设 maxPages。每卡含 Image + 2 个 backdrop-blur 覆盖层 + 按钮，50 页 × 40 张即 2000 卡片常驻。

**修复**：架构级：需分列虚拟化（如 TanStack Virtual 自定义 lanes）或 useInfiniteQuery `maxPages` 配合双向翻页，超出本期最小修改范围，先记录不动代码。

**复核**：证据属实：L69 pages.flat() + L83 全量 map，useInfinitePosts.ts L12-21 确未设 maxPages；post-card 实含 Image + 2 处 backdrop-blur 元素（评级 chip L60、收藏按钮 L76）+ 底部渐变层，证据描述基本准确。DOM 无界增长是真实 perf 隐患而非约束 5 所列的新功能。该发现已按约束 7 自我限定：架构级、标 low、仅记录不动代码，处理方式完全符合硬约束。

### [LOW] stagger-sequence (L87)

**问题**：交错延迟用全局 flat 索引计算，首页交错正确（40ms、封顶 240ms），但无限滚动追加的每一页因 i>=6 全部命中 240ms 封顶：新卡片先空白 240ms 再齐步出现，页内交错失效

**证据**：83 行 `{flat.map((post, i) => (`，87 行 `style={{ animationDelay: \`${Math.min(i, 6) * 40}ms\` }}`——i 是所有已加载页拼接后的全局索引；fade-in-up 为 fill both（tailwind.config.ts 56 行），延迟期卡片保持 opacity:0。

**修复**：按页内索引计算延迟：渲染改为 pages 双层 map（外层页、内层卡片），delay 用 `Math.min(页内序号, 6) * 40`，让每次追加从 0ms 重新交错、保留 240ms 封顶。

**复核**：证据属实：L83 全局索引 i、L87 Math.min(i,6)*40、tailwind.config.ts L56 fade-in-up 为 fill both（delay 期间保持 from 态 opacity:0）。行为核实：卡片 key 为 post.id，已有节点不重挂、动画不重放，仅新增节点入场；追加页所有卡全局 i≥40 全部命中 240ms 封顶，齐步出现、页内交错失效。可见场景真实存在——用户滚到哨兵处等待时（L93-94 骨架在视口内），新卡就在视口里空白 240ms 后同时弹出。双层 map 按页内索引是最小局部修改；提醒：若与 index 1 的拆列重构同批落地，delay 应在拆列分发前按页内序号先算好，两个 fix 需协调实现。low 恰当。

## frontend/components/browse/post-card.tsx

### [MEDIUM] color-contrast (L60)

**问题**：分级角标文字压在 bg-black/40 半透明底上直接叠图片，白底/亮色图（画廊常见）最劣情况下 explicit 红字只有约 2.4:1、safe 绿字约 3.9:1，11px 文字远低于 4.5:1。

**证据**：post-card.tsx L59-61 芯片类名 `"absolute bottom-2 left-2 ... text-[11px] font-medium opacity-0 ... group-hover:opacity-100", "bg-black/40 backdrop-blur-sm", rc.text`。WCAG 实算（纯白图为底）：仅芯片自身 40% 黑遮罩时底≈rgb(153,153,153)，questionable #eab308=1.44:1、safe=1.24:1、explicit=1.33:1；即使叠加 L54 悬停渐变（from-black/70 在芯片高度约 52% 黑）后底≈rgb(73,73,73)，explicit 仍只有 2.39:1、safe 3.94:1、questionable 4.56:1。

**修复**：把 L60 的 `bg-black/40` 提到 `bg-black/90`：白图最劣情况下 explicit 4.62:1、safe 7.61:1、questionable 8.82:1 全部 ≥4.5 ✓，深色图上视觉几乎无差异，保留 backdrop-blur-sm 与三色分级身份。

**复核**：代码属实（L59-61 bg-black/40 + rc.text）。独立重算 WCAG：白图+黑40%底 rgb(153,153,153) 时 safe 1.25、questionable 1.49、explicit 1.32；叠加悬停渐变（芯片中部 α≈0.54）后 explicit 2.51、safe 4.14、questionable 4.92，芯片顶部（α≈0.46）explicit 仅 2.03、safe 3.36。与指控数值方向一致（其 questionable 4.56 与我算的 4.69 有小出入，不影响结论）。芯片可见时渐变必然同时可见（同为 group-hover 同时长），故真实最劣约 explicit 2.0-2.5:1，仍严重低于 4.5:1。fix bg-black/90 经实算白图最劣 explicit 4.65、safe 7.68、questionable 9.12，全部达标，且为单类名最小改动。与 #10 重复。

### [MEDIUM] keyboard-nav (L59)

**问题**：分级角标和底部渐变只在 group-hover 时显现，键盘 Tab 到卡片收藏按钮时它们仍是 opacity-0，键盘用户永远看不到分级信息。

**证据**：post-card.tsx L54 渐变 `... opacity-0 transition-opacity duration-200 group-hover:opacity-100`、L59 芯片 `... opacity-0 transition-opacity duration-200 group-hover:opacity-100`；对比 L76 收藏按钮自己有 `focus-visible:opacity-100`，但焦点进入卡片不会触发 group-hover，芯片/渐变无 focus 变体，分级信息（title 提示同样键盘不可达）对键盘用户丢失。

**修复**：在 L54 渐变和 L59 芯片的类名里各加 `group-focus-within:opacity-100`，使焦点落在卡片内任一控件时角标随渐变一起显现。

**复核**：代码属实：L54 渐变与 L59 芯片均只有 group-hover:opacity-100，无任何 focus 变体；全仓库 grep 无 group-focus-within/focus-within，globals.css 仅对 .card-fav 做了触屏常显。卡内唯一可聚焦元素是收藏按钮（自身 focus-visible:opacity-100），Tab 进入不会触发 group-hover，分级信息（title 提示也仅鼠标可见）对键盘用户完全不可达，违反项目硬性键盘可达要求。Tailwind v3.4.17 原生支持 group-focus-within:，fix 有效且最小。与 #3/#16 重复。

### [MEDIUM] hover-vs-tap (L54)

**问题**：卡片上的分级 chip（safe/q/e 关键信息）和底部渐变只在 group-hover 时显示；键盘 Tab 聚焦到收藏 ★ 时按钮自己会现身（focus-visible:opacity-100），但分级 chip 仍不可见——分级信息对键盘用户完全不可达。

**证据**：L54 渐变: `... opacity-0 transition-opacity duration-200 group-hover:opacity-100`；L59 chip: `... opacity-0 transition-opacity duration-200 group-hover:opacity-100`——两处都只有 group-hover，无 group-focus-within。而 L15 注释声称 "Hover (or focus) surfaces … a rating chip"，实际未实现 focus 路径。

**修复**：给 L54 渐变 div 和 L57-59 chip span 的类名各加 `group-focus-within:opacity-100`，与收藏按钮的 focus 显现行为对齐。

**复核**：与 #1 同一缺陷，证据独立核实成立：L54/L59 仅 group-hover、无 focus 路径；L16 注释确实写了 Hover (or focus) surfaces… a rating chip（行号 15→16 小偏差在允许范围），即注释承诺的 focus 路径未实现。fix 与 #1 相同且有效。建议与 #1/#16 合并为一条。

### [MEDIUM] consistency (L31)

**问题**：收藏 toast 是用户可见文案，却带工单号和「接口」等开发内部黑话，违反项目硬约束 8（UI 文案不得出现工单号/接口名）。

**证据**：post-card.tsx:31 `toast(fav ? "已取消收藏（待 #8 接口）" : "已收藏（待 #8 接口）");`

**修复**：改为不含内部黑话的文案：`toast(fav ? "已取消收藏（暂未保存）" : "已收藏（暂未保存）")`。

**复核**：L31 逐字属实：toast(fav ? "已取消收藏（待 #8 接口）" : "已收藏（待 #8 接口）")。「#8」是工单号、「接口」是开发黑话，直接违反项目硬约束 8。fix 为最小文案替换，且「（暂未保存）」保留了未持久化的诚实提示（注释 L19-20 证实收藏仅本地视觉）。与 #14/#15 重复，medium 恰当。

### [MEDIUM] color-accessible-pairs (L60)

**问题**：分级 chip 的 rating 色文字在 bg-black/40 半透明遮罩上，白色图片最差情况下对比度仅 1.25–1.49:1，三个分级色全部严重不达 WCAG AA (4.5:1)，chip 内容在亮图上不可读

**证据**：L57-62: <span className={cn("absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-medium ...", "bg-black/40 backdrop-blur-sm", rc.text,)}；rc.text 来自 lib/colors.ts L9-13 (text-safe/text-questionable/text-explicit)。实算（WCAG 相对亮度）：遮罩底=0.4黑+0.6白=#999999 (L=0.3185)；safe #22c55e (L=0.4108) → 1.25:1；questionable #eab308 (L=0.4975) → 1.49:1；explicit #ef4444 (L=0.2290) → 1.32:1，全部 << 4.5:1。即使叠加悬停时下方 from-black/70 渐变（chip 位置 α≈0.55）计算：safe 4.22:1、explicit 2.55:1 仍不达标

**修复**：把 L60 的 "bg-black/40 backdrop-blur-sm" 改为 "bg-black/90 backdrop-blur-sm"。实算验证：白图最差情况合成底色 #1a1a1a (L=0.0100)，safe 7.68:1、questionable 9.12:1、explicit 4.65:1 全部 ≥4.5；纯黑图下 explicit 亦有 6.58:1。仅一个类的改动，保留玻璃拟态 backdrop-blur 与现有视觉身份

**复核**：对比度失败本身经独立重算成立，fix 数值亦验证正确（bg-black/90 白图最劣：safe 7.68、questionable 9.12、explicit 4.65，全部 ≥4.5）。但 headline 的 1.25-1.49:1 对应「芯片可见而渐变不可见」的状态——该状态实际不存在（两者同为 group-hover:opacity-100 同 duration-200，永远同显同隐），真实可见态最劣约 explicit 2.0-2.5:1、safe 3.4-4.1:1（其 evidence 附带的渐变计算 safe 4.22/explicit 2.55 与我一致）。另 evidence 中「纯黑图下 explicit 6.58:1」为算术笔误，实为 5.58:1（仍达标）。综合：hover 才出现的辅助角标、与 #0 重复且 #0 评 medium，一类名即修，high 偏高。

### [MEDIUM] form-copy-quality (L31)

**问题**：收藏星标的 toast 文案「已收藏（待 #8 接口）」把工单号和「接口」内部黑话直接暴露给用户，且「已收藏」实际并未持久化，提示语误导。

**证据**：post-card.tsx L31: toast(fav ? "已取消收藏（待 #8 接口）" : "已收藏（待 #8 接口）");（注释 L19-20 自述 favorite 仅为本地视觉、API 未接）

**修复**：改为 `toast(fav ? "已取消收藏（暂未保存）" : "已收藏（暂未保存）")`，两个分支都如实标注未持久化；失败时才 toast 的策略留待 #8 接入真实 API 后再考虑。

**复核**：L31 文案与 L19-20 注释（favorite 仅本地视觉、API 落在 #8）均属实：工单号+「接口」黑话violates硬约束 8，且「已收藏」未持久化确有误导。fix 的前半正确；但「只在失败时 toast」建议在当前无 API、无失败路径的实现下是空操作，且纯「已收藏」反而加重误导，应保留「暂未保存」说明。与 #7/#15 重复。

### [MEDIUM] spec-no-dev-jargon (L31)

**问题**：收藏 toast 是用户可见文案，却带工单号「#8」和「接口」内部黑话。

**证据**：L31 `toast(fav ? "已取消收藏（待 #8 接口）" : "已收藏（待 #8 接口）");`

**修复**：两分支对称处理：`toast(fav ? "已取消收藏（暂未保存）" : "已收藏（暂未保存）")`（与 #7 的 fix 一致）。

**复核**：L31 证据逐字属实，与 #7/#14 同一缺陷（三条重复），违反硬约束 8 成立，medium 恰当。fix 的小问题：只给「已收藏」分支加了「暂未保存」注记，而「已取消收藏」同样未持久化，两分支诚实度不对称；且「功能完善中」略冗余。

### [MEDIUM] spec-keyboard-parity (L59)

**问题**：分级角标和底部渐变只在 group-hover 时显示，键盘用户 Tab 到收藏按钮时只看到按钮本身（focus-visible:opacity-100），分级信息对键盘用户永远不可见，指针/键盘信息不对等。

**证据**：L59 角标 `opacity-0 transition-opacity duration-200 group-hover:opacity-100`（无 focus 变体）；L54 渐变层同样只有 `group-hover:opacity-100`；L76 收藏按钮自身才有 `focus-visible:opacity-100`。

**修复**：给 L59 角标和 L54 渐变层的类串各追加 `group-focus-within:opacity-100`，焦点进卡片即与 hover 同步显示。

**复核**：与 #1/#3 完全相同的缺陷，证据独立核实成立（L54/L59 无 focus 变体、L76 按钮自身才有 focus-visible:opacity-100、全仓库无 group-focus-within）。fix 相同且在 v3.4.17 下有效。severity 与重复条目不一致：键盘可达是项目硬性 first-class 要求，同缺陷在 #1/#3 均为 medium，统一为 medium。

### [LOW] alt-text (L38)

**问题**：卡片图片 alt 只是「图片 {id}」，读屏用户听到的整页是几十个「图片 42」式的无信息文本，起不到描述作用。

**证据**：post-card.tsx L38 `alt={`图片 ${post.id}`}`；lib/types.ts 的 PostSummary（L28-36）只有 id/rating/is_animated 等字段、无标签数据，卡片是页面主要内容而 alt 不含任何内容线索。

**修复**：先用现有字段充实：`alt={`图片 ${post.id}，分级 ${post.rating}${post.is_animated ? "，动图" : ""}`}`；真正描述性的 alt（如 Danbooru 惯例用标签串）需要列表接口在 PostSummary 里补 tags 字段，属架构级改动，故本条仅标 low。

**复核**：代码属实：L38 alt=`图片 ${post.id}`；types.ts L27-36 PostSummary 确无 tags 字段（注释 no full tag set 属实），列表页 alt 无任何内容线索。发现自身已把完整方案标为架构级并降为 low，短期用现有字段充实 alt 是最小局部修改；rating 原值为英文（safe 等），但 L63 title 已是 `分级：${post.rating}` 同款写法，与现状一致。与 #17 重复。

### [LOW] cursor-pointer (L76)

**问题**：收藏 ★ 按钮缺 cursor-pointer（原生 button 默认 cursor:default），是全项目唯一没手型的可点元素，与其余按钮的约定不一致。

**证据**：L76: `"card-fav absolute top-2 right-2 h-9 w-9 rounded-full flex items-center justify-center backdrop-blur-sm transition-all duration-200 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"` — 类名中无 cursor-pointer。

**修复**：在该 cn() 基础串里加 `cursor-pointer`。

**复核**：代码属实：L75-80 类名无 cursor-pointer。唯一性经 grep 核实：Button 基元（button.tsx:6）及仓库内其余全部原生 button（dropdown-menu 46/81、password-input 30、settings 72、tag-drawer 17、safe-mode-toggle 38）均带 cursor-pointer，收藏钮是唯一例外（sheet 背景遮罩为 aria-hidden 非控件，不计）。加 cursor-pointer 为最小修改且符合项目惯例。low 恰当。

### [LOW] press-feedback (L76)

**问题**：卡片收藏 ★ 按钮无按下反馈（无 active: 态），点击瞬间只有 toast，按钮本身无物理反馈。

**证据**：L76 类名含 `transition-all duration-200 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 …` 但无 active:*。

**修复**：类名加 `active:scale-95`（或对齐 Button 基元的 active:scale-[0.97]）；若同时采纳 #13 的过渡收窄，把 transform 一并列入 transition-[...] 或接受按压缩放为瞬时切换。

**复核**：证据属实：L76 无 active:* ，且项目惯例存在（Button 基元有 active:scale-[0.97]）。但 summary 中「点击瞬间只有 toast，按钮本身无物理反馈」言过其实：点击即刻切换 bg-black/50→bg-safe/90 并填充星形（L77-79），按钮本身有强烈的即时状态反馈，缺的仅是按下瞬间的 active 微态，故只能算 low 中的轻微项。fix 可用（transition-all 会带过渡）；若同时采纳 #13 收窄过渡属性需把 transform 纳入或接受按压即时缩放。

### [LOW] transform-performance (L35)

**问题**：卡片 hover 用默认 transition 属性集把 box-shadow（e1→e2，30px 模糊）纳入 200ms 动画逐帧重绘；收藏按钮（自带 backdrop-blur-sm）用 transition-all。

**证据**：post-card.tsx L35：`transition duration-200 ease-out-soft hover:scale-[1.02] hover:shadow-e2 hover:z-10`（Tailwind 默认 transition 集包含 box-shadow）；L76：`"card-fav absolute top-2 right-2 h-9 w-9 rounded-full flex items-center justify-center backdrop-blur-sm transition-all duration-200 opacity-0 group-hover:opacity-100 ..."`。光标在网格上掠过多张卡片时连续触发阴影重绘。

**修复**：L35 `transition` 改 `transition-transform`（阴影改为直接切换）；L76 与 #13 合并处理，用 `transition-[opacity,background-color] duration-200 ease-out-soft`（若采纳 #5 的 active:scale 则写成 transition-[opacity,background-color,transform]）。

**复核**：证据属实：L35 用默认 transition（Tailwind v3 默认属性集确含 box-shadow，e1→e2 为 30px 模糊大阴影，hover 期间逐帧重绘）；L76 transition-all 属实。属真实但轻微的绘制开销，low 恰当。注意 L76 的建议与 #13 重复且 #13 版本更完整（补了 ease-out-soft）；transition-[opacity,background-color] 的逗号任意值在 v3 合法。

### [LOW] consistency (L59)

**问题**：评级 chip 用任意值字号 text-[11px]，脱离字号刻度；同类 chip 基元 Badge（badge.tsx:6）为 text-xs，同为 px-2 py-0.5。

**证据**：post-card.tsx:59 `...rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-medium...`；badge.tsx:6 `...px-2 py-0.5 text-xs font-medium...`

**修复**：把 `text-[11px]` 改为刻度值 `text-xs`。

**复核**：两处证据逐字核实：post-card.tsx:59 text-[11px]、badge.tsx:6 px-2 py-0.5 text-xs font-medium。同为胶囊型小标签基元而字号刻度不一致成立（Badge 为 rounded-md、芯片为 rounded-full，但字号对比不受影响）。text-xs 为最小修改。与 #9/#11 重复，low 恰当。

### [LOW] readable-font-size (L59)

**问题**：卡片分级 chip 使用 text-[11px]（11px < 12px 下限），且为任意值写法脱离字号刻度

**证据**：post-card.tsx L59: "absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-medium opacity-0 transition-opacity duration-200 group-hover:opacity-100"

**修复**：将 text-[11px] 改为标准刻度 text-xs（12px），chip 内容仅为图标加 safe/q/e 单字符标签，12px 不会撑破 py-0.5 圆角胶囊

**复核**：证据逐字属实（L59 text-[11px]）。11px 低于 12px 可读下限且为任意值写法成立；芯片内容仅 Shield 图标 + safe/q/e 单字符，改 text-xs 后胶囊尺寸变化 ≈1px，不会破版。与 #8/#11 同一缺陷同一修复，建议合并。low 恰当。

### [LOW] min-text-size (L59)

**问题**：分级 chip 用 text-[11px]，是全站唯一 <12px 的文本，也是唯一脱离字号体系的任意值（全站字号清单：11/12/14/16/18/20px，其余均成体系）

**证据**：L59: "absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-medium opacity-0 transition-opacity duration-200 group-hover:opacity-100"。grep 全 frontend 确认这是唯一的 text-[...] 任意字号；其余为 text-xs(12)/text-sm(14)/base(16)/text-lg(18)/text-xl(20)

**修复**：text-[11px] 改为 text-xs（12px），回归 Tailwind 标准字号体系，chip 尺寸几乎不变

**复核**：grep 全 frontend 独立核实：text-[ 任意字号仅 post-card.tsx:59 一处，唯一性claim成立；Badge/Button 等均用标准刻度。与 #8/#9 同一缺陷（三条重复），fix 相同且最小。low 恰当。

### [LOW] easing (L45)

**问题**：同一卡片内 easing 混用：容器缩放用 ease-out-soft，但图片淡入、底部渐变、分级 chip、收藏钮四处过渡都落在 Tailwind 默认 ease，同一次 hover 手势里两种缓动并行

**证据**：35 行容器 `transition duration-200 ease-out-soft hover:scale-[1.02]`；对比 45 行 `"w-full h-auto block transition-opacity duration-300"`、54 行 `opacity-0 transition-opacity duration-200 group-hover:opacity-100`、59 行 `opacity-0 transition-opacity duration-200 group-hover:opacity-100`、76 行 `transition-all duration-200`——均未写 easing，回退到默认 cubic-bezier(0.4,0,0.2,1)。

**修复**：在 45/54/59/76 四处补 `ease-out-soft` 类，与 35 行容器统一。

**复核**：四处证据逐行核实：L45/L54/L59/L76 均未写 ease-*，回退到 Tailwind 过渡工具类自带的 cubic-bezier(0.4,0,0.2,1)，而 L35 容器用 ease-out-soft，同一次 hover 中缩放与三层淡入确实并行两种缓动。小瑕疵：L45 图片淡入发生在加载时而非 hover 手势内，列入「同一手势」略有凑数，但统一补 ease-out-soft 无害且符合 token 惯例（Button/topbar 均用）。low 恰当。

### [LOW] transition-scope (L76)

**问题**：收藏按钮实际只过渡 opacity 与 background-color，却用 transition-all，连 backdrop-filter/transform 等都被纳入（这是全仓库仅有的两处 transition-all 之一，另一处为 topbar.tsx:41）

**证据**：76 行 `"card-fav absolute top-2 right-2 h-9 w-9 rounded-full flex items-center justify-center backdrop-blur-sm transition-all duration-200 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 ..."`——状态变化只有 opacity（group-hover/focus-visible/fav 常显）与 hover:bg-black/70 的背景色。

**修复**：改为 `transition-[opacity,background-color] duration-200 ease-out-soft`；若同时采纳 #5 的 active:scale-*，则用 `transition-[opacity,background-color,transform]`。

**复核**：证据属实且唯一性经 grep 核实：全仓库 transition-all 仅 topbar.tsx:41 与 post-card.tsx:76 两处；该按钮实际变化只有 opacity 与背景色。fix 语法在 v3 合法（transition-[opacity,background-color] 会保留默认时距并被 duration-200/ease-out-soft 覆盖），且比 #6 的 L76 版本完整。唯一遗漏：若同时采纳 #5 的 active:scale 需把 transform 列入。low 恰当，与 #6 的 L76 部分重复。

### [LOW] spec-alt-text (L38)

**问题**：卡片 alt 只有「图片 {id}」，未按规范「brief alt from tags/source」提供语义信息；完整满足需列表接口带标签，属架构级，现有字段可先小改充实。

**证据**：L38 `alt={`图片 ${post.id}`}`；lib/types.ts L27-36 PostSummary 无 tags 字段（注释 "no full tag set, to keep payload small"），组件侧拿不到标签。

**修复**：短期小改：用现有字段充实 alt，如 `alt={`图片 ${post.id}，分级 ${post.rating}`}`；完整符合规范需 PostSummary 增加代表性标签字段（架构级，留给后续切片）。

**复核**：与 #2 同一缺陷，证据核实成立：L38 alt 属实，types.ts L27 注释「no full tag set, to keep payload small」逐字存在，组件侧确实拿不到标签。发现已自我限定为 low + 短期小改（用 rating 充实 alt），完整方案正确地标注为架构级留给后续切片，未越界。建议与 #2 合并，并可顺带把 is_animated 一起写入（如 #2 的 fix）。

## frontend/components/browse/safe-mode-toggle.tsx

### [MEDIUM] state-clarity (L39)

**问题**：安全模式开关在开启态（safe_mode 默认即为 true，最常见状态）没有任何 hover 反馈：hover:text-foreground 只写在关闭态分支，桌面优先产品下开启态悬停无视觉响应。

**证据**：safe-mode-toggle.tsx:39 `On ? "bg-safe/15 text-safe" : "bg-surface text-muted hover:text-foreground",`

**修复**：开启态分支补 hover 类：`On ? "bg-safe/15 text-safe hover:bg-safe/25" : "bg-surface text-muted hover:text-foreground"`。

**复核**：L39 与 evidence 逐字一致：开启态（safe_mode ?? true，默认且最常见）无任何 hover 类，关闭态有 hover:text-foreground，不对称属实。自算 WCAG 对比度验证 fix 无回退：text-safe #22c55e（L≈0.411）叠在 bg-safe/25 混合 #0a0a0b 后 ≈#103920（L≈0.031），对比 ≈5.7:1 > 4.5:1 AA。桌面优先下顶栏常用控件默认态零悬停反馈，medium 恰当；fix 为 token 化的单类添加。

### [LOW] aria-labels (L35)

**问题**：安全模式开关同时使用「随状态翻转的动作式 aria-label」和 aria-pressed，读屏输出「关闭安全模式 切换按钮 已按下」造成双重否定歧义。

**证据**：safe-mode-toggle.tsx L34-35 `aria-pressed={safeMode}` 与 `aria-label={safeMode ? "关闭安全模式" : "开启安全模式"}`。ARIA 切换按钮的惯例是二选一：固定名称+aria-pressed 表状态，或变动名称不带 aria-pressed；两者混用时用户无法确定当前到底开没开。

**修复**：把 L35 改为固定 `aria-label="安全模式"`，状态完全交给 aria-pressed（可见文本「安全/全部」与 title 提示保持不变）。

**复核**：L34-35 与 evidence 完全一致：aria-pressed={safeMode} 与动作式动态 aria-label 并存。ARIA APG 切换按钮规范明确要求二选一；safeMode=true 时读屏输出「关闭安全模式 切换按钮 已按下」确实可被理解为'安全模式已关闭'，与真实状态相反。fix 是单属性最小改动，固定名「安全模式」也仍包含可见文本「安全」（WCAG 2.5.3 label-in-name 无回退）。a11y 是项目一等要求，low 合理。

### [LOW] cursor-pointer (L38)

**问题**：安全模式开关禁用时（未登录或切换中）仍显示手型光标：有 cursor-pointer 和 disabled:opacity-50，但没有禁用态光标处理。

**证据**：L38: `"inline-flex items-center gap-1.5 h-10 px-3 rounded-md text-sm transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"` — 无 disabled:cursor-not-allowed（grep 确认 cursor-not-allowed 仅存在于 input/password-input）。

**修复**：类名加 `disabled:cursor-not-allowed`（与 ui/input.tsx L10 的写法一致）。

**复核**：L38 类名与 evidence 逐字一致，且该按钮也没有 Button 基类的 disabled:pointer-events-none，因此禁用态（未登录/isPending）悬停确实显示手型。grep 复核：cursor-not-allowed 全项目仅 ui/input.tsx L10 与 ui/password-input.tsx L20。fix 与 input 惯例一致且保留 title 提示（若改用 pointer-events-none 会失去 title），是合适的最小修改。

### [LOW] press-feedback (L38)

**问题**：安全模式开关无按下反馈（无 active: 态）；项目基线 ui/button.tsx 有 active:scale-[0.97]，自定义按钮没跟上。

**证据**：L38 类名含 `transition-colors cursor-pointer focus-visible:…` 但无任何 active:*（grep 确认 active: 全项目仅出现在 ui/button.tsx L6）。

**修复**：类名加 `active:scale-[0.97]`，并把 `transition-colors` 改为 `transition`（让 scale 也有过渡），与 Button 基线一致。

**复核**：grep 复核：active: 全项目仅 ui/button.tsx L6（active:scale-[0.97]），该手写按钮确实无任何按下反馈，与项目按钮基线不一致。transition-colors 改 transition 后 scale 才有过渡，做法正确；globals.css 已全局处理 prefers-reduced-motion（transition-duration 强制 0.01ms），加 scale 无动效风险。与 index 5 合并后最终为 transition ease-out-soft（可再补 duration-150 与基线完全一致）。

### [LOW] weight-hierarchy (L38)

**问题**：三个手写按钮（安全模式切换、标签抽屉触发、设置页退出登录）字重为默认 400，与 ui/button.tsx 基类的 font-medium(500) 不一致，违反按钮 500 的字重层级

**证据**：safe-mode-toggle.tsx L38: "inline-flex items-center gap-1.5 h-10 px-3 rounded-md text-sm transition-colors cursor-pointer ..."（无 font-medium）；同样：tag-drawer.tsx L17 触发按钮、app/settings/page.tsx L72 退出登录按钮。对照 components/ui/button.tsx L6 基类含 "text-sm font-medium"

**修复**：在三处手写按钮的 className 中补 font-medium：safe-mode-toggle.tsx L38、tag-drawer.tsx L17、app/settings/page.tsx L72，使按钮字重统一为 500

**复核**：四处引用全部核实：safe-mode-toggle.tsx L38、tag-drawer.tsx L17、settings/page.tsx L72 均无 font-medium；ui/button.tsx L6 基类含 text-sm font-medium。顶栏中 TagDrawer 触发器与 SafeModeToggle 并排，与任何 Button 实例同屏即现字重不一致。fix 为三处各加一个类，最小且合惯例。low 恰当。

### [LOW] easing (L38)

**问题**：颜色过渡未带 ease-out-soft token（默认 ease），与 Button 基类的规范写法不一致；同类还有 badge.tsx:6 的 transition-colors 和 settings/page.tsx:72 的裸 transition

**证据**：38 行 `"inline-flex items-center gap-1.5 h-10 px-3 rounded-md text-sm transition-colors cursor-pointer ..."` 无 easing；对比 button.tsx 6 行规范写法 `transition duration-150 ease-out-soft`。badge.tsx 6 行 `text-xs font-medium transition-colors`、settings/page.tsx 72 行 `hover:bg-explicit/10 transition cursor-pointer` 同样缺 token。

**修复**：三处（safe-mode-toggle.tsx:38、components/ui/badge.tsx:6、app/settings/page.tsx:72）各补 `ease-out-soft`，与 Button 基类统一。

**复核**：证据核实：toggle L38 transition-colors、badge.tsx L6、settings L72 均无 easing token；ease-out-soft 确为项目 token（tailwind.config.ts transitionTimingFunction['out-soft']，button.tsx 与 topbar.tsx 已在用）。两点保留意见不影响成立：(1) 措辞小误——Tailwind transition 默认 timing 是 cubic-bezier(0.4,0,0.2,1) 而非 CSS ease；(2) Badge 当前无消费者且 variants 无 hover 色，其 transition-colors 目前是惰性的，补 token 属无害的一致性整理。核心锚点（toggle/settings 的交互元素与 Button 基线动效不一致）成立，low 恰当，fix 最小。

## frontend/components/browse/search-box.tsx

### [HIGH] narrow-grace (L26)

**问题**：375px 宽度下顶栏必然横向溢出：搜索框 form 是 flex-1 但没有 min-w-0，无法收缩到 input 固有最小宽度以下，把用户菜单按钮挤出视口

**证据**：search-box.tsx L26: <form onSubmit={submit} className={cn("relative flex-1 max-w-md", className)} role="search">；容器 topbar.tsx L45: <div className="h-full mx-auto max-w-[1800px] px-4 flex items-center gap-3">。宽度估算（<640px 文字标签已 sm:hidden）：px-4=32 + 4×gap-3=48 + logo 28(h-7 w-7, topbar.tsx L51) + 标签按钮≈40(px-3+16px 图标, tag-drawer.tsx L17) + 安全模式按钮≈40(safe-mode-toggle.tsx L38) + 账户按钮 40(h-10 w-10, dropdown-menu.tsx L52) = 228px 固定开销；375px 时搜索框仅剩 147px，而 flex 项 min-width:auto 使 form 最小宽度等于 <input> 固有宽度（约 170–200px，Input 为 w-full px-3），溢出约 25–50px；320px 时缺口约 80px，账户菜单按钮被推出屏幕右缘（fixed 顶栏内溢出内容直接被裁掉、不可达），违反「<768px 不破版不溢出」硬要求

**修复**：在 search-box.tsx L26 的 form className 中加 min-w-0：cn("relative min-w-0 flex-1 max-w-md", className)。input 本身是 w-full，会随 form 一起收缩，320–767px 下五个控件即可全部放下

**复核**：逐条核对全部属实：search-box.tsx L26 确无 min-w-0；topbar.tsx L45/L51、tag-drawer.tsx L17、safe-mode-toggle.tsx L38、dropdown-menu.tsx L52 引用逐字匹配。重算固定开销：px-4=32 + 4×gap-3=48（TagDrawer 的 Sheet 关闭时 return null 且开启时 portal 到 body，故顶栏恰为 5 个流内 flex 子项、4 个 gap）+ logo 28 + 标签钮 40 + 安全钮 40 + 账户钮 40 = 228px，与 evidence 一致。input 固有宽度（默认 size=20，text-sm+px-3+边框）约 165–180px，flex 项 min-width:auto 使 form 无法收缩到该值以下，最小总宽约 395–410px > 375px，确实溢出；header 为 fixed，fixed 元素溢出不产生可滚动区域，账户菜单（含设置/退出登录）在 320–400px 下真实不可达。属「<768px 不破版不溢出」硬要求的破版问题而非触摸 UX，在范围内。fix 加 min-w-0 是该类 flexbox 收缩问题的标准最小修法，符合项目 Tailwind 惯例；severity high 恰当。

### [HIGH] back-behavior (L22)

**问题**：搜索提交用 router.replace 覆盖当前历史记录，连续搜索后按浏览器后退无法回到上一次搜索结果，而是直接退出画廊历史。

**证据**：search-box.tsx:22 `router.replace(q ? `/?${next.toString()}` : "/");` — 每次提交都替换当前 history 条目；先搜 A 再搜 B 后按后退，不会回到 ?tags=A。

**修复**：把第 22 行的 router.replace 改为 router.push：`router.push(q ? `/?${next.toString()}` : "/");`，让每次搜索产生一条历史记录（可选：提交前若 next.toString() 与当前 params 相同则 return，避免重复条目）。

**复核**：L22 代码逐字属实：router.replace 每次提交覆盖当前 history 条目。app/(protected)/page.tsx L9-11 通过 useSearchParams 响应式读取 tags，改 push 后按后退即可恢复上一次搜索结果，前提成立。此处是显式回车提交（非边输边搜的 debounce 场景——Next.js 官方只在后者用 replace 防刷屏），显式搜索用 push 是通用惯例，且组件注释自称「URL state, shareable」。搜索是本画廊的核心导航循环，连搜两次按后退直接被弹出应用历史，high 合理。fix 为一词改动、最小且无副作用（push 与 replace 滚动行为一致），建议一并做 fix 中已提的可选去重（next.toString() 与当前 params 相同则 return）。小提醒（不影响裁决）：value 用 useState 只初始化一次，后退/前进后输入框文字不会随 URL 同步，属相邻问题，可另行处理。

## frontend/components/browse/tag-drawer.tsx

### [MEDIUM] escape-routes (L24)

**问题**：标签抽屉内没有任何可见的关闭控件，只能靠 Esc 或点击遮罩关闭，不知道 Esc 的用户（尤其读屏用户，抽屉内无任何可聚焦控件）会被困在抽屉里。

**证据**：tag-drawer.tsx L23-25 头部 `<div className="p-4 border-b border-border flex items-center justify-between"><h2 className="font-medium">标签筛选</h2></div>` 用了 justify-between 但右侧为空；sheet.tsx 中遮罩层 L44-47 为 aria-hidden 的纯 onClick div，无键盘/读屏可达的关闭方式提示。

**修复**：与 #6 合并执行：在 tag-drawer.tsx 头部 h2 后加 <button type="button" onClick={() => setOpen(false)} aria-label="关闭标签筛选" className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:text-foreground hover:bg-surface cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"><X className="h-4 w-4" /></button>，并把 L3 改为 import { Tags, X } from "lucide-react"。

**复核**：证据逐字属实：tag-drawer.tsx L23-25 头部 justify-between 右侧为空；sheet.tsx L43-47 遮罩是 aria-hidden 的纯 onClick div，L31-33 只有 Esc，面板内无任何可聚焦子控件。「被困」对键盘用户略夸大（Esc 可用、面板 open 时获焦），但 aria-modal=true 把读屏虚拟光标限制在对话框内、遮罩又对 AT 隐藏，不知道 Esc 的读屏/纯鼠标用户确实没有任何可发现的关闭入口。可见关闭钮是对话框标准构件，属可达性补全（硬约束 6 键盘可达性 first-class），不算新功能。与 index 6 为同一问题，应合并为一次修改。

### [MEDIUM] consistency (L27)

**问题**：标签抽屉正文对用户暴露工单号「#7」和接口名「GET /api/tags」，违反硬约束 8（不得出现工单号、接口名）。

**证据**：tag-drawer.tsx:27 `标签树数据待 #7 接入（GET /api/tags）。届时这里按类型折叠展示热门标签。`

**修复**：三条合并，统一采用 index 5 的措辞：「暂无可筛选的标签。导入图片后，这里会按角色 / 作品 / 画师等分类展示热门标签。」——本条原 fix 的「即将上线」是营销口吻且面板已存在，空态措辞更准确。

**复核**：tag-drawer.tsx L27 文案逐字属实，含工单号「#7」与接口名「GET /api/tags」，直接违反硬约束 8 与任务 PRD R4（验收标准有专项「用户可见文案无开发黑话」）。工单信息已在 L7-8 代码注释里保留，改 UI 文案无信息损失。与 index 5/7 指同一处，合并为一次修改。

### [MEDIUM] empty-states (L27)

**问题**：标签抽屉的空态文案整段是开发内部话术，含工单号「#7」和接口名「GET /api/tags」，违反用户可见文案不得出现内部黑话的要求。

**证据**：tag-drawer.tsx L26-28: <div className="p-4 text-sm text-muted"> 标签树数据待 #7 接入（GET /api/tags）。届时这里按类型折叠展示热门标签。 </div>

**修复**：文案改为用户语言，例如「暂无可筛选的标签。导入图片后，这里会按角色 / 作品 / 画师等分类展示热门标签。」——删除「#7」与「GET /api/tags」，其余结构不动。

**复核**：L26-28 逐字属实，违反 PRD R4/硬约束 8。三条同类发现（2/5/7）中本条的替换文案最佳：是真正的空态用户语言，且「角色 / 作品 / 画师」与 lib/colors.ts 的标签分类体系（character/copyright/artist）对齐。以本条文案为最终版本，合并执行一次。

### [MEDIUM] modal-escape (L24)

**问题**：标签抽屉只有 Esc 和点击遮罩两种关闭方式，面板内没有可见关闭按钮，三者缺一（不用键盘的用户看不到任何关闭入口）。

**证据**：tag-drawer.tsx:23-25 `<div className="p-4 border-b border-border flex items-center justify-between"><h2 className="font-medium">标签筛选</h2></div>` — justify-between 右侧为空；Sheet 仅实现 Esc（sheet.tsx:31-33）与遮罩点击（sheet.tsx:44-47），未渲染关闭按钮。

**修复**：在 tag-drawer.tsx 抽屉头部 h2 之后补一个关闭按钮：`<button type="button" onClick={() => setOpen(false)} aria-label="关闭标签筛选" className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted hover:text-foreground hover:bg-surface cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"><X className="h-4 w-4" /></button>`（lucide X 图标）。

**复核**：证据属实（行号偏差在容忍内：Esc 在 sheet.tsx L31-33、遮罩在 L43-47）。Sheet 只实现 Esc + 遮罩点击，未渲染任何关闭按钮；模态三件套（Esc/遮罩/可见按钮）缺可见项，纯鼠标用户看不到显式关闭入口，读屏用户在 aria-modal 内无可发现出口。fix 的类名完全符合项目惯例（focus-visible ring-accent、hover:bg-surface）。与 index 0 重复，建议保留本条更完整的按钮写法作为最终修改，注意补 lucide X 的 import。

### [MEDIUM] spec-no-dev-jargon (L27)

**问题**：标签抽屉占位文案对用户直接暴露工单号「#7」和接口名「GET /api/tags」。

**证据**：L27 `标签树数据待 #7 接入（GET /api/tags）。届时这里按类型折叠展示热门标签。`

**修复**：统一采用 index 5 的空态措辞「暂无可筛选的标签。导入图片后，这里会按角色 / 作品 / 画师等分类展示热门标签。」，不用「即将上线」句式。

**复核**：L27 逐字属实，违反 PRD R4/硬约束 8。与 index 2/5 完全重复（同一行同一问题），合并为一次修改即可。

### [LOW] press-feedback (L17)

**问题**：顶栏“标签”按钮无按下反馈（无 active: 态）。

**证据**：L17: `"inline-flex items-center gap-1.5 h-10 px-3 rounded-md text-sm text-foreground hover:bg-surface cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"` — 无 active:*。

**修复**：类名加 active:scale-[0.97] transition duration-150 ease-out-soft——button.tsx 的按下缩放是配合 transition 生效的，只加 active 会显得生硬；顺带也让现有 hover:bg-surface 有了与 Button ghost 一致的过渡。

**复核**：L17 类名逐字属实，确无任何 active:* 态；全库 grep 确认 active: 仅出现在 ui/button.tsx 基类（active:scale-[0.97]），即项目确有按下反馈约定而这个绕过 Button 组件的自定义按钮漏掉了。属实但影响很小，low 恰当；注意按 PRD R3，low 级本任务只记录进 research/spec 备忘、不实施。

### [LOW] line-height (L26)

**问题**：多行中文正文段落（抽屉空态、设置卡片描述、画廊空态副文案）用 text-sm 默认行高 20/14≈1.43，低于正文 1.5 的下限，中文多行阅读偏挤（全库无任何 leading-* 类）

**证据**：tag-drawer.tsx L26-28: <div className="p-4 text-sm text-muted">标签树数据待 #7 接入（GET /api/tags）。届时这里按类型折叠展示热门标签。</div>（w-80 抽屉内约 3 行）；同类多行点：app/settings/page.tsx L29 描述 p、masonry-grid.tsx L75 空态副文案。grep 确认全 frontend 无 leading-* 类

**修复**：首要目标：tag-drawer.tsx L26 的段落加 leading-relaxed（换成新空态文案后仍约 2-3 行）；settings/page.tsx L29 与 masonry-grid.tsx L75 顺手加无害，可一并统一，单行标签/按钮不动。

**复核**：已自行重算：Tailwind text-sm 默认 14px/20px≈1.4286，确实低于 1.5；grep 确认全 frontend 零 leading-* 类，证据属实。修正两点：抽屉正文在 w-80 减 p-4×2 = 288px 内约 2 行而非「约 3 行」（不影响定性，仍是多行）；settings L29 与 masonry L75 在桌面宽度基本单行，只有 <768px 才换行、而该档硬约束只要求不破版，真正桌面多行的只有抽屉这一段。WCAG AA 无行高硬指标（1.5 属 AAA/排版基线），故为纯打磨项，low 恰当；按 PRD R3 本任务只记录不实施。

## frontend/components/browse/topbar.tsx

### [HIGH] keyboard-nav (L42)

**问题**：顶栏滚动隐藏后只有鼠标 hover 能唤回，但隐藏时（opacity-0、非 display:none）内部的 logo/标签/搜索/开关/菜单仍在 Tab 顺序里，键盘焦点会落进一条看不见的顶栏，焦点指示完全不可见。

**证据**：topbar.tsx L40-43 `className={cn("fixed top-0 inset-x-0 z-40 h-14 ... transition-all duration-200 ease-out-soft", hidden && !hovering ? "-translate-y-full opacity-0" : "translate-y-0 opacity-100",)}`；唤回条件只有 L38-39 的 onMouseEnter/onMouseLeave 和滚动方向（L28-29），没有任何 focus 处理。用户 PageDown 使顶栏隐藏后按 Tab，焦点进入 L46 的 Link 等控件但页面上看不到焦点环（WCAG 2.4.7）。

**修复**：在 header 的基础类里加 `focus-within:translate-y-0 focus-within:opacity-100`（Tailwind 变体优先级高于条件类，键盘焦点进入时顶栏必定复现；也可等价地加 onFocusCapture={() => setHovering(true)} / onBlurCapture={() => setHovering(false)}）。

**复核**：逐行核实：L42 隐藏分支只有 -translate-y-full opacity-0，无 visibility/inert/pointer-events 处理，opacity-0 元素仍在 Tab 序列；唤回仅有 L28 滚动与 L38-39 鼠标事件，全 frontend 源码 grep 无 focus-within。Topbar 在 (protected)/layout.tsx 中位于 children 之前，Tab 第一下就进入不可见的 L46 Link。违反 PRD 硬约束6（键盘可达性硬要求）与验收标准「焦点始终可见」（WCAG 2.4.7）。fix 的特异性论证正确：focus-within:translate-y-0 生成 (0,2,0) 选择器压过 (0,1,0) 的 -translate-y-full。与 #2/#7/#9 同根，一处改动全部消除。

### [HIGH] scroll-hide-reveal (L42)

**问题**：顶栏下滑隐藏后只靠鼠标 hover / 上滑恢复显示，键盘 Tab 进入顶栏（logo、标签按钮、搜索框、安全开关、账户菜单均可聚焦）时它仍是隐藏的，焦点落在看不见的控件上，搜索输入也不可见。

**证据**：L38-42: `onMouseEnter={() => setHovering(true)}` / `onMouseLeave={() => setHovering(false)}` + `hidden && !hovering ? "-translate-y-full opacity-0" : "translate-y-0 opacity-100"` — 只有鼠标事件参与恢复，整个文件无 onFocus/focus-within 处理（全局 grep 确认 frontend 无 focus-within）。

**修复**：把 L42 隐藏分支改为 `"-translate-y-full opacity-0 focus-within:translate-y-0 focus-within:opacity-100"`（纯 Tailwind 一处类名改动，焦点进入顶栏内部即恢复显示，失焦后照常隐藏）。

**复核**：与 #0 同一缺陷（证据均核实：L38-42 真实、全库无 focus-within 属实、五个内部控件确均可聚焦）。把 focus-within 类加在隐藏分支或基础串效果等价（变体靠特异性取胜，与源顺序无关）。修复时与 #0/#7/#9 合并为一处改动即可。

### [HIGH] search-accessible (L42)

**问题**：顶栏滚动隐藏后仅移出视口未移出焦点序列，键盘用户 Tab 会聚焦到不可见的搜索框/标签/账户菜单，且焦点进入不会让顶栏重新显示。

**证据**：topbar.tsx:42 `hidden && !hovering ? "-translate-y-full opacity-0" : "translate-y-0 opacity-100"` — 隐藏态只有 transform+opacity，无 visibility/inert/pointer-events 处理；显示条件只有滚动（24-34 行 onScroll）和鼠标 hover（38-39 行 onMouseEnter），没有任何焦点触发。header 为 fixed 定位，聚焦离屏元素时浏览器也不会滚它入视口。

**修复**：不用 onFocusCapture，改为与 #0/#2/#9 统一的纯 CSS 方案：在 topbar.tsx L41 基础类串追加 `focus-within:translate-y-0 focus-within:opacity-100`（焦点在顶栏内的整个期间强制可见，滚动再触发 setHidden 也不会盖过它；四条同根发现一处改动全部解决）。

**复核**：与 #0/#2 同根，证据核实无误且补充了正确细节：header 为 fixed 定位，浏览器聚焦离屏元素时不会将其滚入视口。但其 fix 有缺陷：onFocusCapture={() => setHidden(false)} 是一次性的——焦点停在搜索框内时用户滚轮下滑，L29 会再次 setHidden(true)，顶栏带着焦点重新隐藏；CSS focus-within 方案在焦点存续期间持续生效，严格更优。

### [HIGH] spec-keyboard-parity (L42)

**问题**：顶栏滚动隐藏后只能靠鼠标 hover 唤回，键盘 Tab 进入隐藏顶栏时焦点落在完全不可见的控件上（opacity-0 元素仍可聚焦），没有键盘等价的唤回手段。

**证据**：L38-39 `onMouseEnter={() => setHovering(true)} onMouseLeave={() => setHovering(false)}`；L42 `hidden && !hovering ? "-translate-y-full opacity-0" : "translate-y-0 opacity-100"` — 隐藏态未用 display:none/visibility:hidden/inert，Logo 链接、标签按钮、搜索框、安全模式开关全部保持可聚焦但不可见。

**修复**：在 L41 基础类串里追加 `focus-within:translate-y-0 focus-within:opacity-100`（变体选择器特异性 0,2,0 高于 `-translate-y-full`/`opacity-0` 的 0,1,0，焦点进入即唤回顶栏）；或给 header 加 `onFocusCapture={() => setHovering(true)} onBlurCapture={() => setHovering(false)}`。

**复核**：与 #0/#2/#7 同一缺陷，证据核实无误（隐藏态确未用 display:none/visibility/inert，所列控件确均可聚焦），fix 的特异性计算（0,2,0 > 0,1,0）验证正确。severity 调整为 high 与同根三条对齐：PRD R1 明确将「焦点可达性、键盘路径」列为 critical/high 必修，同一缺陷不应因 dims 不同而降级。

### [LOW] aria-labels (L49)

**问题**：顶栏 logo 链接的 aria-label="图库首页" 完全覆盖了可见文本「PM Gallery」，违反 Label in Name（WCAG 2.5.3），语音控制用户念出可见文字无法命中该链接。

**证据**：topbar.tsx L46-55：`<Link href="/" className="flex items-center gap-2 font-semibold text-foreground shrink-0" aria-label="图库首页">` 而 L54 可见文本为 `<span className="hidden sm:inline">PM Gallery</span>`，可访问名称「图库首页」不包含可见文本「PM Gallery」。

**修复**：把 L49 改为 `aria-label="PM Gallery 图库首页"`（可访问名称包含可见文本），或桌面端直接删掉 aria-label 让文本自然命名。

**复核**：L49 aria-label="图库首页" 与 L54 可见文本「PM Gallery」核实无误；aria-label 在可访问名称计算中覆盖内容，桌面端（≥sm 文本可见，正是本里程碑目标端）构成真实的 WCAG 2.5.3 Label in Name 违规。lucide 图标 svg 不贡献名称，删掉 aria-label 后名称自然为「PM Gallery」，两个 fix 选项均成立且为最小改动。low 恰当（仅影响语音控制用户）。

### [LOW] transform-performance (L41)

**问题**：带 backdrop-blur 的固定顶栏使用 transition-all，把所有可动画属性（含 backdrop-filter、边框色、背景色）都纳入过渡，而实际只需要 transform/opacity。

**证据**：topbar.tsx L41：`"fixed top-0 inset-x-0 z-40 h-14 border-b border-border backdrop-blur-md bg-background/70 transition-all duration-200 ease-out-soft"`；L42 切换的只有 `-translate-y-full opacity-0` / `translate-y-0 opacity-100`。顶栏隐藏/显现随滚动方向高频触发。

**修复**：把 `transition-all` 改为 `transition-[transform,opacity]`，其余类不变，过渡只覆盖真正变化的合成器友好属性。

**复核**：L41 transition-all 与 L42 仅切换 transform/opacity 均核实。但需修正影响评估：该元素的 backdrop-filter/border-color/background 值从不变化，transition-all 今天不会真的产生额外过渡动画，实际收益是防御性收敛（防未来类切换意外动画）+ 微量样式追踪开销，非可测性能问题。fix 语法有效（Tailwind 任意属性 transition-[transform,opacity]，duration-200/ease-out-soft 照常生效）。与 #5 重复，保留 low；按 PRD R3，low 级仅记录不实施。

### [LOW] truncation-strategy (L64)

**问题**：账户菜单里的用户名展示无 truncate/title，且菜单容器只有 min-w-[12rem] 无上限，超长用户名会把下拉菜单无限撑宽

**证据**：topbar.tsx L64-66: <div className="px-3 py-2 text-xs text-muted border-b border-border mb-1">{me.data?.username ?? "未登录"}</div>；容器 dropdown-menu.tsx L60: "absolute top-11 z-50 min-w-[12rem] rounded-md ..."（宽度随内容增长）。grep 确认全库无任何 truncate/line-clamp

**修复**：L64 的 div 补 "max-w-[16rem] truncate" 并加 title={me.data?.username ?? "未登录"}，菜单宽度封顶且悬停可见全名

**复核**：证据核实：topbar L64-66 无 truncate/title，dropdown-menu.tsx L60 只有 min-w-[12rem] 无上限，grep 确认全库无 truncate/line-clamp。需修正「无限撑宽」：后端 schemas/auth.py 将 username 限制 max_length=64，最坏约 64 个 CJK 字符 × text-xs ≈ 768px，并非无限，但 right-0 定位的菜单在窄窗口下会溢出视口左缘（违反 <768px 不溢出要求）。fix（max-w-[16rem] truncate + title）最小且符合惯例。

### [LOW] transition-scope (L41)

**问题**：顶栏隐藏/复现只变化 transform 与 opacity，却用 transition-all，把 border-color、backdrop-filter 等无关属性全部纳入过渡

**证据**：41 行 `"fixed top-0 inset-x-0 z-40 h-14 border-b border-border backdrop-blur-md bg-background/70 transition-all duration-200 ease-out-soft"`；42 行实际切换的类只有 `-translate-y-full opacity-0` / `translate-y-0 opacity-100`。

**修复**：把 `transition-all` 收敛为 `transition-[transform,opacity]`，其余类不变。

**复核**：与 #3 完全重复（同一行、同一指控、同一 fix，仅 dims 不同）。证据核实无误，结论同 #3：技术上属实但实际影响是预防性的（无其他属性真的变化），low 恰当，合并处理。

### [LOW] destructive-nav-separation (L74)

**问题**：账户菜单中「退出登录」与普通导航项「设置」紧邻且无分隔线，仅靠红色文字区分，缺少空间分离，误点即刻登出（无确认）。

**证据**：topbar.tsx:67-81 两个 DropdownMenuItem 相邻排列：67-73 行「设置」项之后 74-81 行直接是 `<DropdownMenuItem className="flex items-center gap-2 text-explicit" onClick={() => logout.mutate()} ...>`，中间无分隔元素（dropdown-menu.tsx 也未提供 Separator）。

**修复**：在 topbar.tsx 的「设置」与「退出登录」两个 DropdownMenuItem 之间插入分隔线：`<div role="separator" aria-orientation="horizontal" className="my-1 h-px bg-border" />`（沿用 --border token，符合 shadcn 菜单惯例）。

**复核**：证据核实：L67-81 两项紧邻，dropdown-menu.tsx 确无 Separator 导出，text-explicit（--explicit #ef4444）仅靠红色区分；且 L64 用户名头部本就有 border-b 分隔，破坏性项前反而没有，更显不一致。role="separator" + bg-border 的 fix 最小、走 token、符合 shadcn 菜单惯例（shadcn 惯例正是 logout 前置分隔线而非弹确认，与 #6 的裁决互证）。菜单容器的 onClick 关闭冒泡到分隔线的影响可忽略。

## frontend/components/ui/button.tsx

### [HIGH] color-contrast (L10)

**问题**：主按钮（default 变体）白字压在 --accent 蓝底上对比度仅 3.63:1，低于正文 4.5:1 要求；destructive 变体白字压 --explicit 红底 3.78:1 同样不达标。

**证据**：button.tsx L10 `default: "bg-accent text-accent-foreground hover:bg-accent/90",`、L15 `destructive: "bg-explicit text-white hover:bg-explicit/90",`；globals.css L15-16 `--accent: 217 91% 60%; /* #3b82f6 */`、`--accent-foreground: 0 0% 100%;`，L19 `--explicit: 0 84% 60%; /* #ef4444 */`。WCAG 相对亮度实算：白 L=1.0，accent(hsl 217 91% 60% ≈ rgb(60,131,246)) L≈0.239 → (1.0+0.05)/(0.239+0.05)=3.63:1；explicit L≈0.228 → 3.78:1。按钮文字 text-sm(14px) font-medium 属正常字号，需 ≥4.5:1。登录/初始化页提交按钮「登录」「创建并登录」实际在用 default 变体。

**修复**：把 globals.css 的 --accent 调深一档为 `221 83% 53%`（≈#2563eb）：白字对比升到 5.17:1 ✓，作图标/焦点环等 UI 图形对背景 3.84:1 ≥3:1 ✓，蓝色品牌感不变。destructive 变体不要动 --explicit（它兼任错误文本色需保持亮度），把 L15 底色局部改为 `bg-red-600`（白字 4.83:1 ✓，与 colors.ts 直接用 Tailwind 原色的惯例一致）。

**复核**：证据逐条属实：button.tsx L10/L15、globals.css L15-16/L19 与代码完全一致。自算 WCAG：白字对 accent(hsl 217 91% 60%→rgb(60,131,246)) 为 3.64:1（按 #3b82f6 算 3.68:1），对 explicit(#ef4444) 为 3.76:1，均低于 4.5:1；报告的 3.63/3.78 只是舍入差，结论不变。按钮 text-sm(14px) font-medium(500) 不构成 WCAG 大号文本，4.5:1 适用。调用点属实：login/page.tsx L70「登录」、setup/page.tsx L79「创建并登录」都是无 variant 的 default 按钮，shadcn 基类无任何能补救对比度的样式。属深色主题+键盘/桌面可达性，完全在范围内。fix 数值全部复算通过：白字对 #2563eb=5.17 ✓、#2563eb 对背景=3.83≥3 ✓、白字对 red-600=4.83 ✓、保留 --explicit 使错误文本 5.26 不受损 ✓；副作用核查：焦点环 5.44→3.83 仍≥3，bg-accent/15 图标 3.14 仍≥3。唯一注意点：colors.ts tagCategoryColor 的 text-accent 芯片文字会从 3.94 降到 2.98，但该函数当前零调用点且现值本就低于 4.5，接线时另行处理即可，不影响本 fix 成立。severity high 恰当：全站默认按钮+两个入口页主 CTA 的 AA 文本失败。

### [LOW] spec-contrast-aa (L15)

**问题**：destructive 变体白字配 explicit 红底对比度仅 3.76:1，低于 WCAG AA 正文 4.5:1（按钮文字 text-sm 14px 非大号文本）；当前无调用点，属设计系统级隐患，任何后续危险操作按钮都会继承。

**证据**：L15 `destructive: "bg-explicit text-white hover:bg-explicit/90",`。实算：--explicit=#ef4444 线性化 R=0.863/G=B=0.058，相对亮度 L=0.2126×0.863+0.7152×0.058+0.0722×0.058≈0.229；白色 L=1.0；(1.0+0.05)/(0.229+0.05)=3.76 < 4.5。

**修复**：与 index 0 的 destructive 修法归并、勿重复改同一行：L15 改为 `destructive: "bg-red-600 text-white hover:bg-red-600/90"`（白字静态 4.83:1 ✓、hover 合成后 5.68:1 ✓，与 colors.ts 直接用 Tailwind 原色的惯例一致，保留 --explicit 供错误文本使用）。若 index 0 的 fix 已落地，则本条无需额外改动。原方案 text-background 因 hover 态实算 4.42:1 < 4.5 不予采纳。

**复核**：事实无法推翻：L15 代码逐字属实，数值精确（R=0.863、G=B=0.058、L=0.229、3.76:1 与我复算完全一致），grep 全前端确认 destructive 零调用点，severity low 恰当。不属 out_of_scope：该 variant 是已存在代码，修类名是最小局部修改，不是加新功能。但两点必须修正：(1) 它与 index 0 的 destructive 半条是同一行同一缺陷的重复，两个 fix 对 L15 的改法互相冲突，只能采纳一个；(2) 其自身 fix 在 hover 态自我失效——text-background(#0a0a0b) 压 hover:bg-explicit/90 叠深底后的合成色，实算仅 4.42:1 < 4.5，即悬停瞬间又不达标；且深字压红底偏离项目现有白字压色底的按钮形态。而 index 0 的 red-600 方案静态 4.83、hover 态 5.68 均达标。故确认问题但改写 fix 为与 index 0 归并。

## frontend/components/ui/dropdown-menu.tsx

### [MEDIUM] focus-management (L34)

**问题**：账户菜单声明 role="menu" 却不支持方向键在条目间移动，且 Tab 进条目后按 Esc 关闭时条目被卸载、焦点掉回 body 而不还原到触发按钮。

**证据**：dropdown-menu.tsx L33-35 `const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };` 只关面板不处理焦点；L56-64 `role="menu"` 容器 `onClick={() => setOpen(false)}`，L79 条目 `role="menuitem"`。role=menu 的 ARIA 契约要求箭头键导航；当前焦点在 menuitem 上按 Esc 后该按钮随 open=false 卸载，焦点丢失（WCAG 2.4.3）。

**修复**：给触发按钮加 triggerRef，在 Esc 分支和容器 onClick 关闭时调用 `triggerRef.current?.focus()` 还原焦点；在容器 onKeyDown 里用 ArrowDown/ArrowUp 在 [role=menuitem] 之间 focus 移动（小局部改动）。

**复核**：Evidence 全部核实：L33-35 的 onKey 只做 setOpen(false)；L56-68 面板是 {open && ...} 条件渲染，关闭即卸载；L58 role=menu、L79 role=menuitem，全文件无任何 ArrowDown/ArrowUp 处理。焦点在 menuitem 上按 Esc（或点击条目经 L64 容器 onClick 关闭）后，activeElement 掉回 body，触发按钮不回焦，WCAG 2.4.3 指控成立；role=menu 的 ARIA 契约要求方向键导航也属实。键盘可达性是项目硬性要求（约束6），不受桌面优先豁免。fix 为单文件十几行的小局部改动，且不影响外点关闭（外点不应回焦，原 fix 正确地只覆盖 Esc 与条目点击两条路径），符合该组件 radix-free 最小实现的路线。medium 恰当：条目仍可 Tab 到达，未到不可用程度。

### [MEDIUM] disabled-states (L81)

**问题**：DropdownMenuItem 无任何禁用态样式：顶栏给退出项传了 disabled={logout.isPending}，语义上禁用了，但视觉上不降级（无 opacity），hover 高亮和 cursor-pointer 照常生效，看起来完全可点。

**证据**：L81: `"w-full text-left rounded-sm px-3 py-2 text-sm text-foreground hover:bg-surface cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"` — 无任何 disabled:* 工具类；topbar.tsx L77 传入 `disabled={logout.isPending}`。禁用 button 上 :hover 伪类仍会命中，hover:bg-surface 依旧高亮。

**修复**：在 DropdownMenuItem 基础类名末尾加 `disabled:opacity-50 disabled:pointer-events-none`（shadcn 按钮同款约定，ui/button.tsx L6 已有先例）。

**复核**：Evidence 核实：L81 类名与代码逐字一致，无任何 disabled:* 工具类；topbar.tsx L77 确实给退出项传 disabled={logout.isPending}。禁用 button 上 :hover 伪类与 cursor 样式仍然生效的说法正确，视觉上完全可点。ui/button.tsx L6 已有 disabled:pointer-events-none disabled:opacity-50 先例，fix 与项目惯例完全一致、属一行小改。注意点（不影响裁决）：加 pointer-events-none 后点击禁用项会命中容器 onClick 导致菜单关闭，此行为与 shadcn 约定一致，可接受。组件是通用件且当前就有真实禁用用法，medium 恰当。

### [LOW] press-feedback (L52)

**问题**：账户菜单触发按钮（L52）和菜单项（L81）都无按下反馈（无 active: 态）。

**证据**：L52: `"inline-flex items-center justify-center h-10 w-10 rounded-md text-foreground hover:bg-surface cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"`；L81 菜单项类名同样无 active:*。

**修复**：触发按钮类名加 `active:scale-[0.97]`，DropdownMenuItem 加 `active:bg-surface/80`；建议同时给两者补 `transition duration-150 ease-out-soft`（与 ui/button.tsx L6 同款），按下/hover 过渡更顺，仍是纯加类小改。

**复核**：Evidence 核实：L52 与 L81 类名逐字一致，均无 active:* 态。项目内 ui/button.tsx L6 已确立 active:scale-[0.97] 的按下反馈语言，dropdown 触发钮与菜单项缺失属真实不一致，不是审美偏好。fix 为纯加类的最小改动；菜单项用 active:bg-surface/80 而非缩放的取舍合理（与 button secondary 变体 hover:bg-surface/80 同源）。可选优化：顺带补 transition duration-150 ease-out-soft 与 Button 对齐，但非必须。low 恰当。

### [LOW] elevation-consistent (L60)

**问题**：下拉菜单面板用了原生 shadow-xl，未走项目唯一允许的 shadow-e1/e2 阴影 token。

**证据**：dropdown-menu.tsx:60 `"absolute top-11 z-50 min-w-[12rem] rounded-md border border-border bg-background shadow-xl p-1",`

**修复**：把 `shadow-xl` 改为浮层档 `shadow-e2`。

**复核**：L60 的 shadow-xl 属实；e1/e2 token 真实存在（globals.css L21-23、tailwind.config.ts L31-34）且已被 auth-card(shadow-e2)、settings 页(shadow-e1)、post-card(shadow-e1/e2) 采用，dropdown 走原生 shadow-xl 确属偏离。但两点减分：其一，'项目唯一允许' 说法过强——sheet.tsx L54 同样在用 shadow-xl，说明这只是既有约定而非强制校验；其二，纯视觉一致性问题，面板另有 1px border 兜底，无功能/可达性影响，一词替换级别的修复定 medium 偏高。另外本条与 index 5 是同一行、同一修复的完全重复，报告时应合并为一条。

### [LOW] motion-meaning (L60)

**问题**：账户下拉菜单瞬现瞬隐，无任何进场动效，与 Sheet 背板（fade-in）和网格卡片（fade-in-up）的出现语言不一致

**证据**：56-63 行：`{open && (<div role="menu" className={cn("absolute top-11 z-50 min-w-[12rem] rounded-md border border-border bg-background shadow-xl p-1", ...)}`——条件渲染直接挂载/卸载，className 中无 animate-* 或 transition 类。

**修复**：给 menu 容器加现成的 `animate-fade-in`（150ms，tailwind.config 已定义）表达出现；如需方向感可在 config 加 fade-in-down keyframe（translateY(-4px)→0）。出场瞬时卸载保留即可（延迟卸载属架构级）。

**复核**：Evidence 核实：L56-63 条件渲染直接挂载/卸载，className 无任何 animate-*/transition 类。对照物均属实：sheet.tsx L44 背板有 animate-fade-in，masonry-grid.tsx L86 卡片有 animate-fade-in-up，tailwind.config.ts L55 已定义 fade-in 150ms ease-out——出现动效语言确实已在项目内成型，dropdown 瞬现属不一致。fix 是加一个现成类；reduced-motion 已由 globals.css 全局压到 0.01ms，无额外风险；'出场保留瞬时卸载、延迟卸载属架构级' 的边界把握符合约束7。low 恰当。

### [LOW] spec-token-styling (L60)

**问题**：下拉菜单浮层用原生 shadow-xl，绕开项目专为浮层定义的 elevation token。

**证据**：L60 `"absolute top-11 z-50 min-w-[12rem] rounded-md border border-border bg-background shadow-xl p-1",`；globals.css L21-23 明确注释 `--elevation-2` 用于 "cards / floating layers"，tailwind.config.ts L31-34 已暴露为 shadow-e1/e2。

**修复**：`shadow-xl` 改为 `shadow-e2`，与 SectionCard（shadow-e1）、AuthCard（shadow-e2）同一套 elevation 体系。

**复核**：事实层面全部核实：L60 shadow-xl、globals.css L21-23 的 elevation 注释（'cards / floating layers'）、tailwind.config.ts L31-34 暴露 shadow-e1/e2、auth-card.tsx L34 用 shadow-e2，引用无误，指控成立。但本条与 index 3 是同一行代码、同一处缺陷、同一个一词替换修复，仅规则维度不同（spec vs style），属重复发现——最终报告应与 index 3 合并为一条 low，避免重复计数抬高问题数。

## frontend/components/ui/input.tsx

### [LOW] spec-focus-visible (L10)

**问题**：Input 焦点环没有 ring-offset，而同一登录/设置表单里相邻的 PasswordInput 和 Button 都带 ring-offset-2，同页相邻控件焦点样式不一致（用户名框焦点环贴边、密码框焦点环外扩 2px）。

**证据**：input.tsx L10 `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent`（无 offset）；password-input.tsx L20 含 `focus-visible:ring-offset-2 focus-visible:ring-offset-background`；button.tsx L6 同样带 `focus-visible:ring-offset-2 focus-visible:ring-offset-background`。

**修复**：在 Input 类串中补 `focus-visible:ring-offset-2 focus-visible:ring-offset-background`，与 PasswordInput/Button 对齐。

**复核**：证据逐条属实：input.tsx L10 的焦点类串确实没有 ring-offset；password-input.tsx L20 与 button.tsx L6 均含 focus-visible:ring-offset-2 focus-visible:ring-offset-background（grep 全前端仅这两处用 offset，无全局样式或调用点补偿——login/setup 不传 className，search-box 只传 pl-9）。相邻性属实：login/page.tsx 与 setup/page.tsx 同一表单内 Input（用户名）紧挨 PasswordInput（密码），下方是 Button，键盘 Tab 切换时焦点环样式肉眼可见地不一致。修复可行且方向正确：Tailwind 3.4.17 + theme.extend.colors 定义了 background，ring-offset-background 已在两个兄弟组件中验证可用；三个控件里两个已带 offset，且 shadcn 上游 Input 默认也带 ring-offset-2，给 Input 补类比从 PasswordInput 删 offset 更符合项目与技术栈惯例。属键盘可达性/焦点一致性范畴（项目硬性要求），非新功能、非浅色、非纯移动端。severity low 恰当：两处焦点指示本身都清晰存在（2px accent 环），不构成 WCAG 2.4.7 失败，属一致性打磨。fix 为单行局部类修改，无需调整。

## frontend/components/ui/password-input.tsx

### [MEDIUM] consistency (L20)

**问题**：PasswordInput 焦点环带 ring-offset-2，而同一表单里的 Input（input.tsx:10）无 offset，登录/设置页两个相邻输入框聚焦样式肉眼可见不一致。

**证据**：password-input.tsx:20 含 `focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background`；input.tsx:10 仅 `focus-visible:ring-2 focus-visible:ring-accent`（无 offset）

**修复**：删除 password-input.tsx:20 中的 `focus-visible:ring-offset-2 focus-visible:ring-offset-background` 两个类，与基元 Input 对齐（更稳妥的小重构是内部直接复用 `<Input className="pr-10">` 防止再次漂移）。

**复核**：Evidence 精确属实：password-input.tsx L20 含 focus-visible:ring-offset-2 focus-visible:ring-offset-background，input.tsx L10 无 offset。login/page.tsx L51(Input) 与 L61(PasswordInput) 是同一表单相邻字段，Tab 切换时一个 ring 贴边、一个带 2px 背景色间隙，肉眼可辨。方向核实：全项目仅 button.tsx 用 offset，Input/SafeModeToggle/dropdown 触发器/菜单项均无 offset，故删 PasswordInput 的 offset 与输入基元对齐是正确方向；且该文件整段复制了 Input 类串并已实际漂移，内部复用 <Input className="pr-10"> 的小重构符合惯例（Input 已 forwardRef、接受 type，可直接换用）。无任何文档支持密码框特意加 offset，反而 07-01 任务目标是「focus ring 统一」。medium 恰当（应用入口表单、每次键盘登录可见）。

### [LOW] press-feedback (L30)

**问题**：密码可见性切换（眼睛图标按钮）无按下反馈（无 active: 态）。

**证据**：L30: `"absolute right-2 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded text-muted hover:text-foreground cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"` — 无 active:*。

**修复**：在 L30 类名加 `active:scale-95 transition duration-150 ease-out-soft`（项目 07-01 设计稿明确 icon button 为 active:scale-95 transition，过渡参数与 button.tsx 一致；Tailwind 的 scale 与 -translate-y-1/2 经 transform 变量叠加，不会破坏垂直居中）。

**复核**：Evidence 与 password-input.tsx L30 逐字一致，确无 active:*。推翻失败：press-feedback 是项目真实规范——button.tsx L6 有 active:scale-[0.97]，归档任务 07-01-frontend-visual-polish/design.md L49/L77 明确写了 spec press-feedback/scale-feedback，且规定顶栏 icon button 用 active:scale-95 transition。:active 在桌面鼠标按下同样触发，不属移动端豁免。SafeModeToggle/dropdown 触发器同样缺 active: 只说明问题更普遍，不构成对本文件的反驳。severity low 恰当。

### [LOW] radius-scale (L30)

**问题**：密码可见性切换按钮用裸 `rounded`（0.25rem），脱离项目 rounded-md/lg/xl/full 圆角体系。

**证据**：password-input.tsx:30 `...flex h-7 w-7 items-center justify-center rounded text-muted hover:text-foreground...`

**修复**：把 `rounded` 改为 `rounded-md`（同类小图标按钮如 dropdown 触发器、SafeModeToggle 均为 rounded-md）。

**复核**：Evidence 与 L30 逐字一致。grep 全 frontend 证实裸 rounded 仅此一处；同类小图标按钮均为 rounded-md：dropdown-menu.tsx L52 触发器、safe-mode-toggle.tsx L38、topbar.tsx L51 的 logo 徽标（同为 h-7 w-7）。指控措辞有小瑕疵——项目还用了 rounded-sm（dropdown-menu.tsx L81 菜单项），所以圆角体系是 sm/md/lg/xl/full 而非仅 md/lg/xl/full；但这不构成反驳：裸 rounded(4px) 仍是全库孤例，且同尺寸兄弟组件全部 rounded-md。tailwind.config 未定义 radius token（仅覆写 xl），故属一致性问题而非 token 违规，low 恰当，fix（rounded→rounded-md）最小且合惯例。

## frontend/components/ui/sheet.tsx

### [HIGH] focus-management (L35)

**问题**：Sheet 打开时焦点移入面板但关闭后不还原到触发按钮（焦点掉回 body），且 aria-modal="true" 却没有焦点圈闭，Tab 会穿出抽屉进入被遮罩的页面内容。

**证据**：sheet.tsx L29-37 effect 只有 `panelRef.current?.focus();` 和 Esc 监听，cleanup 仅 `removeEventListener`，无 opener 记录；L50-52 `role="dialog" aria-modal="true" tabIndex={-1}`。Esc 关闭后面板卸载，document.activeElement 落到 body，键盘用户丢失位置；面板内 Tab 不循环，与 aria-modal 语义矛盾。

**修复**：维持原修法，两点补充：1) `const opener = document.activeElement as HTMLElement | null` 必须写在 `panelRef.current?.focus()` 之前，cleanup 里 `opener?.focus()`；2) Tab 圈闭取 panel 内可聚焦元素首尾循环时要处理空列表（当前抽屉是空态，无可聚焦子元素）：列表为空时直接 e.preventDefault() 把焦点留在面板上。与 index 3/4 合并为同一处 ~10 行局部修改。

**复核**：证据逐行核实为真：L29-37 effect 只有 Esc 监听 + panelRef.current?.focus()，cleanup 仅 removeEventListener；L50-52 role=dialog/aria-modal/tabIndex={-1}。全前端 grep 确认没有任何焦点还原或圈闭代码。spec 硬性要求（component-guidelines.md L44 'focus trap inside modals/lightbox; restore focus on close'），键盘可达性是硬约束 6，且本任务 PRD 验收项『纯键盘走查标签抽屉、焦点始终可见』当前必挂——Esc 后 activeElement 落 body。Tab 穿透真实存在：面板 portal 到 body 末尾且当前抽屉内容零可聚焦元素，按一次 Tab 即绕回被遮罩页面的 topbar 按钮。升 high：直接击穿验收标准且属 PRD R1 定义的『焦点可达性/键盘路径』类。注意与 index 3/4 是同一缺陷，只需修一次。

### [HIGH] spec-keyboard-parity (L29)

**问题**：抽屉是 role=dialog + aria-modal="true" 的模态，但关闭后不恢复焦点（焦点掉回 body，键盘用户要从头 Tab），也没有最小的 Tab 焦点圈定，违反 component-guidelines「focus trap inside modals/lightbox; restore focus on close」。

**证据**：L29-37 的 useEffect 只做 Esc 监听和 `panelRef.current?.focus()`，cleanup 仅 `document.removeEventListener`；L51 `aria-modal="true"`；L8 注释自述 "Full focus-trap is deferred"。

**修复**：effect 打开分支开头记录 `const prev = document.activeElement as HTMLElement | null;`，cleanup 里补 `prev?.focus();` 恢复焦点；并在 onKey 里对 Tab 做最小圈定（在 panelRef 内 querySelectorAll 可聚焦元素，Shift+Tab/Tab 到首尾时循环），约十行局部改动。

**复核**：证据属实：L29-37、L51 aria-modal、L8 'Full focus-trap is deferred' 注释均逐字核对无误；spec 引文在 .trellis/spec/frontend/component-guidelines.md L44 逐字存在。代码注释自称『推迟到后续切片』不构成豁免：硬约束清单里推迟的只有灯箱/收藏 API/批量/新页面，而键盘可达性是硬约束 6 且 fix 仅 ~10 行局部代码（约束 7 达标）。与 index 0 是同一缺陷（归还 + 圈闭），同步升 high（理由同 index 0：击穿 PRD 键盘走查验收项），修一次即可，Tab 圈闭需加空列表守卫（当前抽屉为空态，见 index 0 的 adjusted_fix）。

### [MEDIUM] elevation-consistent (L54)

**问题**：侧边抽屉面板用了原生 shadow-xl，未走 shadow-e1/e2 阴影 token。

**证据**：sheet.tsx:54 `"absolute top-0 bottom-0 w-80 max-w-[85vw] bg-background border-border shadow-xl outline-none flex flex-col",`

**修复**：把 `shadow-xl` 改为 `shadow-e2`。

**复核**：L54 引文与代码逐字一致。e1/e2 阴影 token 真实存在（tailwind.config.ts L31-34 → globals.css L21-23，注释明确写 'Elevation scale (cards / floating layers)'），且项目惯例已成型：settings 页 shadow-e1、auth-card shadow-e2、post-card e1/hover:e2。抽屉正是浮层，用原生 shadow-xl 绕开 token 属实，未被任何现有代码满足。dropdown-menu.tsx L60 也用 shadow-xl 不构成豁免（那是另一文件的同类问题）。fix 改一个类即最小修改，e2（0 8px 30px）对浮层量级正确。medium 在本次规范打磨任务的 R2 口径内合理，不调整。注：index 5 被驳回后，本条是 shadow 修正的唯一载体。

### [MEDIUM] motion-meaning (L54)

**问题**：抽屉背板有 fade-in 进场而面板本体零动效瞬现，关闭时整体瞬时卸载，侧滑抽屉的出现/消失因果没有动效表达

**证据**：44 行背板 `className="absolute inset-0 bg-black/60 animate-fade-in"` 有进场动画；48-57 行面板 className `"absolute top-0 bottom-0 w-80 max-w-[85vw] bg-background border-border shadow-xl outline-none flex flex-col"` 无任何 animate/transition 类；39 行 `if (!open || typeof document === "undefined") return null;` 关闭时立即卸载。tag-drawer.tsx 8 行注释也写明 "The shell wires the slide-out"，但滑入动效实际缺失。

**修复**：在 tailwind.config.ts 仿照 fade-in-up 增加 slide-in-left/slide-in-right keyframes（translateX(-100%/100%)→0，200ms cubic-bezier(0.22, 1, 0.36, 1) both），面板按 side 分支追加 `animate-slide-in-left` / `animate-slide-in-right`。出场动画需要延迟卸载状态机，属架构级，可后置不做。

**复核**：证据全部属实：L44 背板有 animate-fade-in，L48-57 面板无任何 animate/transition 类，L39 关闭即卸载，tag-drawer.tsx L8 注释确有 'The shell wires the slide-out'。tailwind.config 只有 fade-in/fade-in-up/shimmer，无滑入 keyframes，全前端 grep 无任何 slide-in/animate-in 用法。且这不只是审美问题——原始设计文档（06-28-gallery-app/design.md L224）明确规定『抽屉/浮层过渡 200-300ms ease-out』，当前实现违反自家设计规范；背板淡入而面板瞬现的割裂每次开抽屉都可见。fix 仿 fade-in-up 手写 keyframes 完全符合项目现有惯例（200ms + cubic-bezier(0.22,1,0.36,1) 与 ease-out-soft token 一致），reduced-motion 已有全局守卫，出场动画标注架构级后置符合约束 7。medium 恰当。

### [LOW] modal-escape (L35)

**问题**：抽屉打开时焦点移入面板，但关闭（Esc/点外）后焦点不归还触发按钮，键盘用户焦点掉回 body 需从头 Tab。

**证据**：sheet.tsx:29-37 的 useEffect 中 `panelRef.current?.focus();`（35 行）只处理打开；cleanup（36 行）仅 `document.removeEventListener("keydown", onKey)`，无焦点归还。注：完整 focus-trap 已在 7-9 行注释声明推迟，本条只针对焦点归还。

**修复**：在同一 useEffect 打开时记录来源：`const prev = document.activeElement as HTMLElement | null;`，cleanup 里追加 `prev?.focus();`，即 Esc/点外关闭后焦点回到「标签」触发按钮。

**复核**：证据属实（L29-37/L35/L36 逐字核对无误），spec 明文要求 restore focus on close（component-guidelines.md L44），指控成立。但本条是 index 0/4 的严格子集（只覆盖焦点归还，不含圈闭），三条应去重为一次修改，勿重复实施。fix 本身正确且最小（记录语句需在 panelRef.current?.focus() 之前，原文顺序已隐含）。作为子集条目保留 low 即可，实际严重度以合并后的 index 0/4（high）为准。

## frontend/hooks/useAuth.ts

### [MEDIUM] error-feedback (L51)

**问题**：退出登录失败时完全静默：useLogout 只有 onSuccess，两个调用点（顶栏菜单、设置页）都是裸 logout.mutate()，网络/后端出错时用户点了没有任何反馈也没有恢复提示。

**证据**：L49-55: `return useMutation({ mutationFn: () => api.logout(), onSuccess: () => { qc.clear(); router.replace("/login"); } });` — 无 onError；调用点 topbar.tsx L76 与 settings/page.tsx L70 均为 `onClick={() => logout.mutate()}`，也未传 onError。

**修复**：在 useLogout 的 useMutation 里加 `onError: () => toast.error("退出登录失败，请重试")`（sonner 的 toast 项目已在 safe-mode-toggle 使用，import { toast } from "sonner" 即可），一处修改覆盖两个调用点。

**复核**：证据逐条属实：useAuth.ts L49-55 的 useMutation 只有 onSuccess（qc.clear + router.replace），无 onError；topbar.tsx L76 与 settings/page.tsx L70 均为裸 logout.mutate()，未传 per-call onError。尝试推翻失败：(1) providers.tsx 的 QueryClient 仅设 queries 默认项，无 mutations 默认 onError，也无 MutationCache/QueryCache 全局处理；(2) api.logout() 走 lib/api.ts 的 request()，非 2xx 会 throw ApiError、断网时 fetch 会 reject，失败路径真实存在，失败时既不跳转也无任何提示，指控成立；(3) 修复前提成立：safe-mode-toggle.tsx 已 import { toast } from "sonner" 并用 toast.error("切换失败，请重试")，<Toaster /> 已挂在 app/layout.tsx L31。fix 为单处一行、覆盖两个调用点、文案简体中文且与现有风格一致，属最小局部修改，符合约束 7/8；severity medium 恰当（罕见失败路径但用户可见的死点击）。

### [MEDIUM] submit-feedback (L49)

**问题**：useLogout 只有 onSuccess 没有 onError，两个调用点（顶栏、设置页）也不处理失败，退出登录失败时完全静默——顶栏下拉还会立即收起（dropdown-menu.tsx L64 菜单容器 onClick={() => setOpen(false)}），用户点了没有任何反馈。

**证据**：useAuth.ts L49-55: return useMutation({ mutationFn: () => api.logout(), onSuccess: () => { qc.clear(); router.replace("/login"); } }); — 无 onError；topbar.tsx L76 与 settings/page.tsx L70 均为裸 logout.mutate()

**修复**：与 index 0 合并为同一条：仅在 useLogout 的 useMutation 中加 onError: () => toast.error("退出登录失败，请重试")（import { toast } from "sonner"），一处修改同时覆盖顶栏与设置页；无需改动 dropdown-menu 的收起行为。

**复核**：事实全部核实：useAuth.ts L49-55 无 onError、两调用点裸 mutate 与 index 0 相同；新增的 dropdown 佐证也逐字属实——dropdown-menu.tsx L64 菜单容器 <div role="menu" onClick={() => setOpen(false)}>，菜单项点击冒泡即收起下拉，连 disabled={logout.isPending} 的 pending 态都随菜单一起消失，加重了『完全静默』。无法推翻。但注意：本条与 index 0 是同一缺陷、同一根因、同一修复（仅规则标签 error-feedback/submit-feedback 与 dims 不同），属重复报告，建议向上游合并为一条计数，避免双重扣分/重复修复。

## frontend/styles/globals.css

### [MEDIUM] reduced-motion-complete (L43)

**问题**：reduce 规则只重置了 animation-duration/transition-duration，没有重置 animation-delay，导致 masonry 卡片的 inline animationDelay 交错路径在减少动效模式下仍然生效

**证据**：globals.css 43-51 行：`@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }`——无 animation-delay 重置。配合 masonry-grid.tsx 87 行 `style={{ animationDelay: \`${Math.min(i, 6) * 40}ms\` }}` 与 tailwind.config.ts 56 行 `"fade-in-up": "fade-in-up 200ms cubic-bezier(0.22, 1, 0.36, 1) both"`（fill both 在延迟期应用 from 态 opacity:0），reduce 用户的卡片仍会空白最长 240ms 后按序弹现，交错动效未被真正关闭。

**修复**：在 globals.css 的 prefers-reduced-motion 块内追加一行 `animation-delay: 0.01ms !important;`，使 inline animationDelay 驱动的交错也被禁用（sonner 与 JS 类切换路径已被现有 duration 覆盖，无需改动）。

**复核**：证据全部属实：globals.css L43-52 的 reduce 块只重置 animation-duration/iteration-count/transition-duration/scroll-behavior，确无 animation-delay；masonry-grid.tsx L87 inline animationDelay 最大 Math.min(i,6)*40=240ms；tailwind.config.ts L56 fade-in-up 带 fill-mode both，延迟期应用 from 态 opacity:0。行为推演成立：reduce 下 duration 塌缩到 0.01ms 但 inline delay 原样生效，卡片在各自延迟期内不可见、随后按 0-240ms 顺序弹现，交错入场编排未被关闭；且 masonry-grid.tsx L21-22 注释自称 reduced-motion 会经 globals.css 全局关掉 stagger，代码自身意图证实这是遗漏而非设计。fix 恰当：在现有 reduce 块加一行 animation-delay: 0.01ms !important，与文件既有 0.01ms 惯例一致、最小局部；全前端 grep 确认 inline animationDelay 是唯一 delay 用法（无 transition-delay/delay-* 工具类），fix 中"其余路径已被 duration 覆盖"的说法准确。motion 可达性属项目一等要求且非移动端豁免项，medium 合理。

### [LOW] transform-performance (L80)

**问题**：骨架 shimmer 动画的是 background-position（逐帧重绘、不走合成器），初始 12 个骨架块加上每张未加载卡片的 inset-0 覆盖层会同时无限重绘。

**证据**：globals.css L80-L89：`.shimmer { background-image: linear-gradient(...); background-size: 200% 100%; background-position: 200% 0; }`；tailwind.config.ts L50-L52 keyframes `shimmer: { to: { backgroundPosition: "-200% 0" } }`、L57 `shimmer: "shimmer 1.4s ease-in-out infinite"`。使用点：skeleton.tsx L8、post-card.tsx L50 `<div className="absolute inset-0 shimmer animate-shimmer" aria-hidden />`。

**修复**：整个 shimmer 自包含在 globals.css 内实现，不再依赖 tailwind keyframe：.shimmer 加 overflow: hidden（不要加 position: relative，否则会覆盖 post-card 覆盖层的 absolute 工具类）；新增 .shimmer::after { content: ""; display: block; width: 200%; height: 100%; } 承载现有三段渐变（token --shimmer-from/--shimmer-to 不变），并直接在 globals.css 写 @keyframes shimmer-sweep { from { transform: translateX(-50%); } to { transform: translateX(0); } }（渐变首尾同色，循环无缝），::after 上应用 animation: shimmer-sweep 1.4s ease-in-out infinite；同步删除 tailwind.config.ts 中 shimmer 的 keyframes/animation 条目，并把 skeleton.tsx L8、post-card.tsx L50 类名里失效的 animate-shimmer 去掉（.shimmer 类保留）。现有 reduce 块选择器含 *::after，伪元素动画仍被正确降级。

**复核**：证据全部属实：globals.css L80-89 的 .shimmer 确实用 background-image + background-size 200% + background-position，tailwind.config.ts L50-52/L57 的 keyframe 只动 backgroundPosition 且 1.4s infinite，使用点 skeleton.tsx L8、post-card.tsx L50 均存在，masonry-grid.tsx L50 初始确为 12 个骨架块，post-card 覆盖层在图片 onLoad 前一直存在。技术判断成立：background-position 是 paint 属性，不在合成器线程（合成器只接 transform/opacity/filter 类），逐帧主线程重绘，多个无限动画同时跑。severity low 恰当（骨架是暂态、影响为省电/低端机流畅度）。但原 fix 有缺陷需改写：(1) 把 tailwind 的 shimmer keyframe 改成 transform 后，元素上仍挂着 animate-shimmer，骨架块/inset-0 覆盖层自身会被整体平移，视觉直接坏掉；(2) Tailwind 只在 animate-shimmer 被使用时才输出 @keyframes shimmer，若为避免 (1) 移除用法，globals.css 里引用该 keyframe 名会悄悄失效；(3) .shimmer 定义在 @tailwind utilities 之后，若给 .shimmer 加 position: relative 会以同特异性后序覆盖 post-card 覆盖层的 absolute 工具类，破坏定位。

## frontend/tailwind.config.ts

### [LOW] easing (L55)

**问题**：fade-in 动画用通用 ease-out，而 fade-in-up 用 out-soft 贝塞尔，两个进场动画 easing 不一致，且 fade-in 未对齐项目的 out-soft token

**证据**：55 行 `"fade-in": "fade-in 150ms ease-out",` 对比 56 行 `"fade-in-up": "fade-in-up 200ms cubic-bezier(0.22, 1, 0.36, 1) both",`；39 行 token 定义 `"out-soft": "cubic-bezier(0.22, 1, 0.36, 1)"`。

**修复**：把 55 行改为 `"fade-in": "fade-in 150ms cubic-bezier(0.22, 1, 0.36, 1)"`，与 out-soft token 同值（Sheet 背板、后续 Dropdown 进场都会随之统一）。

**复核**：证据逐字属实（tailwind.config.ts 第39/55/56行）。ease-out 关键字等于 cubic-bezier(0,0,0.58,1)，与 out-soft 的 cubic-bezier(0.22,1,0.36,1) 确为不同曲线，两个进场动画 easing 不一致成立。且项目自己的动效规范（.trellis/tasks/archive/2026-07/07-01-frontend-visual-polish/design.md:29）明确要求「所有动效统一 token --ease: cubic-bezier(0.22,1,0.36,1)」，button/topbar/post-card 均已用 ease-out-soft，fade-in 是唯一漏网者；它被 sheet.tsx:44 的 Sheet 背板实际使用，非死代码。fix 与第56行现有写法完全同构（animation 简写内无法按名引用 out-soft token，内联 bezier 即项目惯例），一行局部修改，severity low 恰当（150ms 纯透明度淡入视觉差异极小，属 token 一致性问题）。无需调整。

## 已否决（勿重报）

- **confirmation-dialogs** @ frontend/components/browse/topbar.tsx（refuted）：证据本身属实（topbar L74-81、settings L70 均无确认，sonner 已在项目中），但规则适用错误：退出登录不是破坏性/不可逆操作——无数据丢失，重新登录即完全恢复，confirmation-dialogs 类规则针对的是不可挽回的操作；grep .trellis/spec 无任何要求登出确认的项目规范；主流惯例（含 shadcn 官方 dropdown 示例）登出项不加确认、只加分隔线——误点风险正是 #8 分隔线要解决的，且 #8 已独立成条。提议的 toast 确认本身是反模式：sonner 默认约 4 秒自动消失且出现在屏幕角落，用户点「退出登录」后若没注意到角落 toast，体验是「点了没反应」，比无确认更差，也不满足 PRD R2「收益明确」门槛。
- **spec-glassmorphism** @ frontend/components/ui/sheet.tsx（refuted）：引文虽逐字属实（sheet.tsx L54、topbar.tsx L41、auth-card.tsx L34 均核对无误），但规范指控不成立：component-guidelines.md L37 把玻璃拟态明确限定为 '(topbar, info panels)'，而设计文档（06-28 design.md）中『信息面板』特指灯箱左侧半透明浮层信息面板（L201），标签筛选抽屉是另列的独立元素（L196），从无玻璃化要求。所谓『统一模式』也不成立——项目另一个 portal 浮层 dropdown-menu.tsx L60 同样是不透明 bg-background + shadow-xl，即不透明浮层本就是现有浮层惯例，抽屉与之一致；引 topbar/AuthCard 对比属挑选样本。在『不重设计、保持现有视觉身份』的 PRD 约束下，把抽屉改半透明+blur 是无规范依据的自选餐式改观感。其中唯一站得住的半句（shadow-xl→shadow-e2）已由 index 1 完整覆盖，本条无残余价值。（附：即便实施 bg-background/85+blur，实测 WCAG 最坏情形前景 ~14:1、muted ~5.3:1 仍过 AA，故驳回纯因规范范围，非对比度。）
- **weight-hierarchy** @ frontend/components/browse/tag-drawer.tsx（refuted）：四处证据引用全部属实，但规则并未被违反：全库字重是内部一致的两级体系——页面/品牌级标题一律 font-semibold（settings/page.tsx L49、auth-card.tsx L28/L39、topbar.tsx L48），区块/面板级标题一律 font-medium（tag-drawer h2、settings 卡片标题 L28），证据自己就证明了 500 这一档是成体系的而非孤例。抽屉内层级靠字号（16 vs 14px）+ 字重（500 vs 400）+ 颜色（foreground vs muted）三重区分，清晰无歧义；h2 比 h1 轻是正确的层级递减而非「脱节」。「标题必须 600-700」是通用启发式：项目规范 component-guidelines.md 无字重条款，本库也没有使用 shadcn Card 原语（settings 是自定义 SectionCard），CardTitle 惯例不构成约束；且 PRD 约束 3 要求保持现有视觉身份。统一改 600 只是风格偏好，不是规范违规。
- **token-usage** @ frontend/lib/colors.ts（refuted）：Evidence 属实（colors.ts:48/50/52 确为 purple/amber/cyan 调色板类），但 token-usage 规则按项目自己的定义已被满足：component-guidelines.md:34-36 明确规定标签分类色的 token 机制就是「a tagCategoryColor(category) helper returning Tailwind class strings」，且规范本身以裸色相命名（copyright → purple, artist → yellow/amber, meta → cyan）；quality-guidelines.md:33/63 的检查项写的是 tag colors via the tagCategoryColor map（token map），colors.ts 正是该规范的逐字实现（第 42 行注释直接引用 component-guidelines），且 grep 证实 purple/amber/cyan 类在 frontend 源码中仅出现于此一处，集中化成立、并无 ad-hoc。character 用 accent 不是半截迁移的证据：accent 本就是规范要求的 character 蓝（#3b82f6），复用现成 token 是正解，另外三色按规范无对应 token。此外该 fix 自相矛盾：现状 text 用 purple-300（#d8b4fe，对合成底色 purple-500/20 over #141416 ≈ rgb(50,33,67) 的对比度经 WCAG 公式重算约 8.3:1）而 bg/border 用 purple-500；单变量方案的 text-tag-copyright 会把文字渲染成 purple-500（#a855f7），对比度降至约 3.7:1，AA 不达标，同时违背其自称的「保持现有色值不变」与本任务 PRD 验收项「标签分类色不动」（07-03-ui-spec-polish/prd.md:38）；若要视觉忠实则需每类 2 个变量共 6 变量 + 6 条 tailwind 映射，在永久 dark-only 里程碑（无主题切换收益）下属零收益的纯间接层。
- **search-accessible** @ frontend/components/browse/search-box.tsx（refuted）：引用的代码都存在（search-box.tsx L31-38 无清空按钮/无 onKeyDown 属实；preflight.css L245-248 逐字属实），但 evidence 的因果论断是错的：[type='search']{-webkit-appearance:textfield} 并不会隐藏 Chrome/Edge 的原生 ✕——取消按钮是 ::-webkit-search-cancel-button 影子伪元素，UA 样式里自带独立的 appearance:searchfield-cancel-button，只有直接对该伪元素设 appearance:none 才会消失，而项目 CSS（globals.css 已查）没有任何这类规则；Tailwind 用户想去掉这个 ✕ 反而要手写 [&::-webkit-search-cancel-button]:appearance-none，正说明 preflight 不隐藏它。且 globals.css L34-36 设了 color-scheme:dark，原生 ✕ 以浅色渲染在 bg-surface/60 上清晰可见；Chromium 对 type=search 还原生支持 Esc 清空，原生 ✕/Esc 都会派发 input 事件、经 React onChange 更新受控 value。故「没有任何清空按钮、清空只能全选删除再回车」在桌面优先的主力浏览器（Chrome/Edge）上不成立，规则已被原生行为满足。唯一残留是 Firefox（从来不渲染原生 ✕、也无 Esc 清空，与 preflight 无关）的跨浏览器一致性差距，最多算 low 级可选打磨，不是本条所指控的缺陷。
