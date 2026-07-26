# Handoff: PM Gallery 前端重设计(暗房霓虹方案)

## Overview
PM Gallery(类 Danbooru 自托管单用户图库,Next.js 15 + FastAPI + SQLite)的整套前端重设计。信息架构重组为**前台(浏览与筛选)+ 管理面板(后台)**两层;视觉方向为"暗房霓虹":近黑底 + 环境光晕 + 悬浮玻璃层 + 紫青渐变强调。覆盖桌面 7+ 屏、移动端 7 屏与 6 个交互中间态。

## About the Design Files
本包内的 `.dc.html` 文件是 **HTML 设计稿(参考原型)**,展示目标外观与行为,**不是可直接搬运的生产代码**。任务是在目标代码库的现有环境中重新实现这些设计——即项目里已有的 **Next.js 15 (App Router) + TypeScript + Tailwind + TanStack Query** 技术栈,沿用其既有模式(`components/ui/*` 无 Radix 的自研组件、`lib/api.ts` 封装、hooks 目录、HSL CSS 变量 → Tailwind token 的做法)。直接在浏览器打开各 `.dc.html`(同目录需保留 `support.js`、`ios-frame.jsx`)即可查看设计稿。

## Fidelity
**High-fidelity(高保真)**。颜色、字体、间距、圆角、文案均为最终意图,应按像素还原;示例图片为 picsum 占位,实际用 `/media` 缩略图。设计稿为静态画面,滚动隐藏、抽屉动画等运动细节按下文"Interactions"描述实现。

## 信息架构(与现状的差异)
- **首页只做展示与筛选**。原顶栏的"标签抽屉/导入"入口移除;标签管理、导入、重复图、差分、设置全部收进**管理面板**。
- **管理面板入口在右上角用户菜单**(头像 → admin / 管理面板 / 设置 / 退出登录),不在顶栏平铺。
- **左侧筛选栏取代收藏夹导航**:按 作者(artist)/ 标签(连带子母成组)/ 评级 / 仅已收藏 组织;无操作 8 秒自动折叠为 56px 图标条,图钉可常驻。
- **安全模式是首页顶栏的独立按钮**(盾形图标 + "安全模式:开/关"),仍为会话级、服务端权威(PATCH /me/settings)。
- **新增"差分组"概念**(手动维护的同作品差分集合,组内选封面;与 phash 自动重复图互不影响,重复图可一键"转差分入组")。需要后端新表 + API:`variant_groups(id, cover_post_id)` + `variant_group_posts(group_id, post_id)`,以及 posts 详情返回所属组成员。
- 建议路由:前台 `/`(`?tags=`、`?photoId=` 灯箱浮层,非独立路由);管理面板 `/admin/tags`、`/admin/scan`、`/admin/danbooru`、`/admin/duplicates`、`/admin/variants`、`/admin/settings`。

## Screens / Views

### 前台(final-front.dc.html)
1. **首页 · 筛选栏展开**
   - 顶栏:悬浮胶囊,高 56px,左右留 20px 边距、顶部 16px;`rgba(21,21,30,0.72)` + `backdrop-blur(20px)` + 边框 `rgba(255,255,255,0.09)`;内容:26px 渐变圆点 logo + "PM Gallery"(Space Grotesk 700 15px)| 搜索胶囊(flex-1,占位"搜索标签,空格 = 同时满足…",右侧 `/` 快捷键 chip)| 安全模式按钮(渐变淡紫胶囊,盾形图标 + "安全模式:关")| 34px 渐变头像。
   - 用户菜单(点头像):232px 玻璃下拉,`rgba(19,19,28,0.92)`,项:admin(标题区)/ 管理面板 / 设置 / 分隔线 / 退出登录(#f07a68)。
   - 筛选栏:240px 玻璃圆角卡(radius 20);区块:标题行(筛选 + 图钉 + 折叠按钮)、"无操作 8 秒后自动折叠"说明、已选条件 chips(可删)、作者列表(琥珀圆点 + mono 名称 + 计数)、标签(连带成组:母标签 chip 一行,下方左侧 2px 紫线缩进子标签 chips)、评级三个勾选(S/Q/E 各自品牌色)、"仅显示已收藏"渐变开关。
   - 内容:标题行(筛选结果 · 12 张 · 条件摘要)+ 4 列瀑布流(列间 gap 6px,卡 radius 14,悬停态:底部黑渐变 + 评级 chip + id);已收藏卡右上角 26px 半透明圆内实心星(紫 `oklch(0.82 0.14 300)`)。
2. **首页 · 筛选栏折叠**:56px 竖向胶囊图标条(展开箭头、标签 sell 带数字角标、作者 person、评级 shield、收藏 star),悬停即展开。
3. **作者视图**(`/?tags=wlop`):搜索框内挂作者 chip;头部 46px 琥珀图标 + wlop(mono 17px 琥珀)+ artist 徽章 + 统计行;右侧"只看已收藏""排序";下方 3 列瀑布流。
4. **灯箱**(`?photoId=` 浮层):纯黑 `#040407` + 紫晕;主图右侧偏置(right 120px 垂直居中,radius 14,大阴影);左侧 320px 信息浮层(radius 20 玻璃):id + 评级 chip + 关闭;操作行(已收藏渐变胶囊 / 下载 / 原图);作者区(wlop chip + "该作者更多 →" + 4 张 44px 缩略图 + "+23");标签(连带成组嵌套样式,同筛选栏);GENERAL chips;差分区(标题"差分 · 同组 3 张" + 查看全部;56px 缩略图,当前项 2px 紫边框 + "当前",其余带 id);元数据 mono 行(尺寸/入库/来源/md5);底部"← → 翻页 · Esc 关闭"。两侧 44px 玻璃圆形翻页钮;右上 "1 / 1,248" 计数 chip。
5. **登录 / 初始化(同壳)**:居中渐变光点 logo + 360px 玻璃卡(radius 24):标题、用户名/密码胶囊输入(聚焦态:紫边框 + 3px 光圈)、渐变登录按钮;下方说明"首次启动?系统会引导你创建拥有者账户"。

### 管理面板(final-admin.dc.html)
统一外壳:左侧 232px 玻璃导航卡(logo + "管理面板 CONSOLE";导航项:标签管理 / 本地扫描 / Danbooru 抓取 / 重复图(23)/ 差分管理(9)/ 设置;激活态 = 紫青渐变淡底 + 紫边框 + #e6dcff;底部"返回前台" + 媒体占用进度条 12.4/64 GB)。
1. **标签管理**:统计 4 卡(总标签 1,694 / 连带规则 12 / 废弃 8 / 近 30 天新增 127)→ 分类分布条(堆叠横条 + 图例:character #5b8def 342 · copyright #a06ae8 187 · artist #e0a43c 96 · general #6c7078 1,024 · meta #46b8c8 45)→ **连带关系图**(点状网格画布 200px:节点 = 标签 chips,横竖 2px 紫线 + 箭头连接 miku_append → miku → vocaloid、rin 汇入 vocaloid(母);连线中点 17px "×"圆钮删除规则;左下虚线"拖入标签…"槽;交互:拖动标签到目标 = 新建连带)→ 左表(标签/分类/图片数/连带/状态,选中行紫色高亮 + 左侧 2px 紫条)+ 右侧 330px 详情面板(标签 chip + id、五分类切换 chips、图片数/首次/最近、连带链、"为该标签添加连带"、关联图片 62px 缩略 + "+339"、操作:标记废弃(琥珀)/ 查看全部图片)。
2. **本地扫描**(独立页):路径输入 + 选项 chips(递归子目录 / phash 异步判重)+ 渐变"开始扫描";统计瓦片(发现 128 / 入库 96(绿)/ 重复 23(琥珀)/ 跳过 9)+ 进度条 75%;结果表(文件 / 大小 / 状态,状态着色:已入库→#6fce88、phash 近似→#f5c344、跳过→#8d8fa0)。
3. **Danbooru 抓取**(独立页):右上琥珀警示 chip"Cloudflare 拦截直连 · 已走 HTTPS_PROXY";查询输入 + 参数 chips(每页 100 / 最多 5 页 / 仅新来源)+ 渐变"开始抓取";日志控制台卡(`rgba(0,0,0,0.45)` mono 11.5px,完成行绿色);历史任务表(时间/查询/结果)。
4. **重复图**:说明"23 组近似 · 不出现在前台浏览,仍可被收藏";组卡:原图 140px + 渐变"原图"徽章 + 元数据列 | 分隔 | 重复项缩略 + phash 距离/来源 | 操作:查看组 / 换原图。
5. **差分管理**:说明 + 搜索 + 渐变"新建差分组";组卡:组号/作者/张数/建立时间 + "解散组"(红边);成员行:封面 104px(2px 紫边框 + 渐变"封面"徽章)、成员图(下方 id + "设为封面 · 移出")、末尾 104px 虚线"添加差分"槽;底部信息条:重复图可一键"转为差分"入组,转入后不再隐藏。
6. **设置**:玻璃卡列表(安全模式(会话级说明 + 当前状态胶囊)/ 账户 admin + 退出登录(红边)/ 媒体占用进度条 / 关于 v0.3.0)。

### 移动端(final-mobile.dc.html,402×874)
1. **首页**:46px 搜索胶囊(logo 点 + 占位 + 头像);chips 行(筛选·2 渐变 / miku / 安全:关);双列瀑布流;"上滑加载更多"。
2. **筛选抽屉**:底部弹层(radius 24 顶角、拖动把手),背景首页模糊压暗;区块同桌面筛选栏(作者 chips / 嵌套标签组 / S✓Q✓E✓ / 仅已收藏开关);底部渐变"应用筛选 · 显示 12 张"。
3. **灯箱**:全屏图;顶部渐变遮罩(返回 / "#0001 · 1/1,248" / 星标);底部信息半层(评级 + 作者 + 尺寸 + 下载;嵌套标签组;差分 38px 缩略;"左右滑动切换 · 下滑关闭")。
4. **作者视图**:返回 + 琥珀图标 + wlop 头部 + "只看已收藏";双列瀑布流。
5. **管理面板入口**(用户菜单进入):统计 3 卡(图片/标签/媒体占用)+ 列表卡(六项,含 Danbooru"代理"徽章、计数、chevron)+ 红边"退出登录"。
6. **标签管理移动版**:搜索 + 分类 chips + 分布条 + 标签行列表(连带/母·子数/废弃行琥珀底);说明条。
7. **登录**:键盘弹出态,表单同桌面。

### 交互中间态(final-states.dc.html)
搜索联想(匹配前缀高亮、miku 行"连带补全 → vocaloid"、废弃行划线 + "已废弃 · 建议改用 miku"、最近搜索、↑↓/Enter 提示)/ 加载骨架(顶栏 + 筛选栏 + 4 列瀑布流微光块,`shimmer` 1.6s 线性循环,背景 200% 位移)/ 空图库(文案沿用现有:"这里还没有图片 / 导入本地文件夹或抓取 Danbooru 后,图片会出现在这里。" + 两个 CTA)/ 筛选无结果(逐项放宽建议 chips)/ 加载失败("请检查后端是否运行" + mono 错误 + 重试)/ 危险确认弹窗(解散差分组:说明不删图,取消 + 红"解散组")与 Toast(绿:安全模式已开启;紫:已收藏 · #0005;底部居中玻璃胶囊)。

## Interactions & Behavior
- **筛选栏**:无操作 8s 自动折叠为 56px 图标条;悬停任一图标或点展开箭头恢复;图钉切换常驻。宽度动画 240↔56px,220ms `cubic-bezier(0.22,1,0.36,1)`。
- **灯箱**:URL 参数 `?photoId=` 驱动(打开 push、←→ 翻页 replace、Esc/遮罩/返回键 back 关闭;直达禁用翻页,单图接口取数)。移动端:左右滑切换、下滑关闭、信息半层可上拉展开。
- **搜索**:空格 = AND;`/` 聚焦;联想下拉显示分类色、计数、连带链;选废弃标签时给提醒不阻断。
- **安全模式**:点顶栏按钮即 PATCH `/me/settings`,成功后列表 refetch + Toast;会话级,重登恢复开启。
- **收藏(星标)**:卡片悬停(触屏常显)右上星按钮,乐观更新 + Toast。
- **瀑布流**:JS 贪心最短列(沿用现有 masonry-grid 算法),无限滚动 IntersectionObserver(rootMargin 600px);新页卡片 fade-in-up 40ms 阶梯。
- **连带关系图**:拖 chip 到另一 chip = 新建规则(需确认弹窗,提示会回填存量);点连线 × = 删除规则(提示不回收已写入标签)。
- **危险操作**(解散差分组/删除收藏夹等):确认弹窗,主按钮红色系。
- **减少动效**:所有动画尊重 `prefers-reduced-motion`(沿用现有 globals.css 全局关闭)。

## State Management
- 现有 hooks 沿用:`useMe`(safe_mode)、`useInfinitePosts`、`useUpdateSafeMode`、`useLogin/useLogout/useSetup`。
- 新增:`useTagSuggest(prefix)`(防抖 150ms)、`useArtists()`、`useVariantGroup(postId)`、`useDuplicateGroups()`、`useScanJob()/useScrapeJob()`(轮询任务状态)、筛选栏本地状态(选中标签/作者/评级/仅收藏 → 序列化进 `?tags=` 与查询参数)、折叠状态(localStorage:`rail_pinned`)。
- 服务端权威:安全模式、会话;乐观更新:星标、筛选 chips。

## Design Tokens
- 背景:页面 `#07070b`(灯箱 `#040407`;管理/前台通用);环境光晕:`radial-gradient(900px 420px at 85% -5%, rgba(139,102,255,0.16), transparent 60%)` 及青色变体 `rgba(70,180,220,0.10~0.12)`。
- 玻璃层:`rgba(21,21,30,0.72)` + `backdrop-filter: blur(20px)`;弹层/菜单 `rgba(19,19,28,0.90~0.94)` + blur 22-24;边框 `rgba(255,255,255,0.07~0.12)`;卡内分隔 `rgba(255,255,255,0.05~0.08)`;实底卡 `#15151c`。
- 文字:主 `#e8e8f0`;次 `#c9cbd8`;弱 `#8d8fa0`;极弱 `#63657a` / `#77778a`(区块标题 mono 10px 字距 1.5px)。
- 强调:渐变 `linear-gradient(135deg, oklch(0.74 0.16 300), oklch(0.74 0.16 210))`(主按钮文字用深色 `#0d0d14`);星标/选中紫 `oklch(0.82 0.14 300)`;头像渐变 `oklch(0.6 0.14 300) → oklch(0.5 0.12 240)`。
- 标签分类(chip = 15% 底 + 40% 边框 + 亮文字):character `#5b8def`/文 `#8db0f5`;copyright `#a06ae8`/`#c9a4f5`;artist `#e0a43c`/`#f0c674`;meta `#46b8c8`/`#7fd6e4`;general 底 `rgba(139,144,154,0.12)`/文 `#b6bac4`。
- 评级:S `#6fce88`(底 `rgba(89,178,110,0.15)`);Q `#f5c344`;E `#f07a68`。
- 圆角:胶囊/按钮 999;帧内卡 14-20;缩略图 8-12;表格卡 16。
- 字体:UI 中文 **Noto Sans SC**(400/500/700);品牌与拉丁 **Space Grotesk**(500/700);id、路径、元数据、计数 **JetBrains Mono**(400/600)。图标 **Material Symbols Rounded**(20-48 opsz,填充态用 `FILL 1`)。
- 高度基准:顶栏胶囊 56;控件 34-42;移动触控目标 ≥44(34px 图标钮周围留白补足)。
- 动效:`cubic-bezier(0.22,1,0.36,1)` 150-220ms;骨架 shimmer 1.6s linear。

## Assets
- 示例图:`https://picsum.photos/seed/pm01..pm12/...`(占位,替换为 `/media/posts/{id}/preview`)。
- 图标:Google Fonts「Material Symbols Rounded」;建议生产改为 lucide-react(项目现有依赖)按名对应:search/sell/shield/star/tune/settings/logout/download/close/chevron_*/folder_open/cloud_download/content_copy/burst_mode/add_link/brush/warning/info/history/refresh/search_off/photo_library/cloud_off/play_arrow/visibility 等。
- 无位图品牌资产;logo 为渐变圆点 + 文字。

## Files
- `final-front.dc.html` — 前台:首页(展开/折叠)、作者视图、灯箱、登录
- `final-admin.dc.html` — 管理面板:标签管理(含连带关系图)、本地扫描、Danbooru 抓取、重复图、差分管理、设置
- `final-mobile.dc.html` — 移动端 7 屏(依赖 `ios-frame.jsx` 仅作设备外框展示,非实现目标)
- `final-states.dc.html` — 交互中间态 6 屏
- `support.js` — 设计稿运行时(仅供本地打开预览,勿移植)

## 实现建议(对照现有代码库)
- 令牌:替换 `styles/globals.css` 的 HSL 变量组 + `tailwind.config.ts` 色板(上表);字体在 `app/layout.tsx` 用 next/font 换 Noto Sans SC / Space Grotesk / JetBrains Mono。
- 改造:`components/browse/topbar.tsx`(胶囊化 + 用户菜单挂管理入口)、`search-box.tsx`(联想下拉)、`post-card.tsx`(radius 14 / 星标常态)、`masonry-grid.tsx`(骨架换新样式);`tag-drawer.tsx` 废弃,改 `filter-rail.tsx`(自动折叠)。
- 新增:`app/(protected)/admin/*` 六页 + `components/admin/*`(shell/nav/stat-card/implication-graph/variant-group-card…)、`lightbox.tsx`(浮层 + URL 驱动)、`empty-states.tsx`、确认弹窗与 Toast 样式(沿用 sonner,自定义玻璃胶囊外观)。
