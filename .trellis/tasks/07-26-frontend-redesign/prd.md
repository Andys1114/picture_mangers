# 前端重设计(暗房霓虹)总览

## Goal

按设计交付稿 `docs/design/pm-gallery-redesign/`（"暗房霓虹"方案）重新实现整套前端，并把配套缺失的后端能力补齐。旧前端整体保留存档（`frontend-legacy/`），新前端在 `frontend/` 目录从零搭建，复用旧代码的 `lib/api.ts` / hooks / `components/ui/*` 模式。

这是**父任务**：只负责需求总集、子任务地图、跨子任务验收和最终集成检查，不直接承载实现。

## 背景与关键认定（来自 2026-07-26 grilling 会话）

- `项目前端.zip` 里是**高保真 HTML 设计稿 + README**，不是可运行代码；"使用新前端" = 按稿重新实现。
- 设计稿 README 明确要求沿用现有技术栈与模式：Next.js 15 (App Router) + TypeScript + Tailwind + TanStack Query，`components/ui/*` 无 Radix 自研组件、`lib/api.ts` 封装、HSL CSS 变量 → Tailwind token。
- 信息架构重组为**前台（浏览与筛选）+ 管理面板（/admin/*）**两层。

## 已敲定的决策

1. **落地方式**：`git mv frontend frontend-legacy`（保留历史 + DEPRECATED 说明，不再维护、不删除）；新 `frontend/` 重写；`dev.py` 指向新前端。决策记录见 ADR `docs/adr/0002-frontend-rewrite-keep-legacy.md`。
2. **范围**：前后端一起做，分 7 个子任务，每个子任务独立可验收。
3. **收藏暂缓**：星标 + 命名收藏夹这次**都不做**（新前端第一版无星标按钮、无"仅显示已收藏"筛选）；后端收藏接口与术语表概念保持不动；收藏界面留待将来独立任务。
4. **差分组语义**（已写入 CONTEXT.md）：组员全部正常出现在瀑布流；封面只是代表图；一图最多属一组；重复图"转差分"= 清 `duplicate_of_id` + 入组，两套机制独立。
5. **评级筛选 × 安全模式**：安全模式开 → S/Q/E 勾选禁用（服务端强制 safe）；关 → 勾选生效、默认全选。
6. **字体自托管**（`next/font/local` + 仓库内 woff2：Noto Sans SC / Space Grotesk / JetBrains Mono）；**图标用 lucide-react**（按设计稿 README 的名称对照表）。

## 子任务地图（按此顺序执行）

| # | 任务 | 内容 | 后端改动 |
|---|------|------|----------|
| 1 | `07-26-front-base` 前台基座与切换 | 目录切换、脚手架、令牌/字体、顶栏、筛选栏（标签+评级）、瀑布流、灯箱、登录/初始化、空/骨架/错误态、移动端响应式 | posts 列表加评级多选参数 |
| 2 | 筛选与联想增强 | 筛选栏作者区、搜索联想下拉 | 作者列表接口（带计数）、标签联想接口（前缀+连带链+废弃提示） |
| 3 | 管理面板基座 + 标签管理页 | admin 外壳/导航、统计卡、分类分布、标签表格+详情面板、连带关系图 | 标签统计接口、连带规则增删 API |
| 4 | 扫描页 + 抓取页 | 本地扫描、Danbooru 抓取两个管理页 | 抓取/扫描历史列表接口（任务接口已有） |
| 5 | 差分组 | 差分管理页、灯箱差分区 | 新表 `variant_groups` / `variant_group_posts` + CRUD API + posts 详情带组员 |
| 6 | 重复图管理页 | 重复图分组视图、换原图、转差分 | 重复图分组接口、换原图接口、转差分接口（依赖 5） |
| 7 | 设置页 + 收尾 | 设置页、媒体占用展示、文档清理与父任务集成验收 | 媒体占用接口 |

子任务 2-7 在启动时再逐个 `task.py create --parent 07-26-frontend-redesign`，避免一次建空壳。

## 跨子任务验收标准

- [ ] 全程 `frontend-legacy/` 保持原样可手动运行（仅 README 加废弃说明），git 历史经 `git mv` 保留。
- [ ] 每个子任务合入后 `dev.py` 起的新前端可用，不出现"半成品页面入口挂在导航上"（未完成的管理页不显示入口或显示"建设中"占位）。
- [ ] 视觉按设计稿像素还原：设计令牌（色板/圆角/字体/动效曲线）统一从 `styles/globals.css` + `tailwind.config.ts` 出，不允许页面内散落硬编码色值。
- [ ] 所有动效尊重 `prefers-reduced-motion`。
- [ ] 收藏（星标/收藏夹）在新前端任何界面都不出现，直至专门任务恢复。
- [ ] 后端每个新接口有 pytest 覆盖；前端 `npm run lint` + `tsc --noEmit` 全绿。
- [ ] 全部子任务完成后：CONTEXT.md 的"前端界面"条目更新为新信息架构（浏览页筛选栏、管理面板），设计稿 README 与实现的偏差记录在本任务 notes。

## Notes

- 设计稿源文件：`docs/design/pm-gallery-redesign/`（README.md 是权威规格；`.dc.html` 直接浏览器打开可看效果，`support.js`/`ios-frame.jsx` 仅供预览勿移植）。
- 设计稿中的星标/已收藏元素（卡片星标、灯箱已收藏按钮、"仅显示已收藏"开关、紫色 Toast 示例）按决策 3 一律**跳过不实现**。
