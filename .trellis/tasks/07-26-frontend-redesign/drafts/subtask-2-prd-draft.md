# 【草稿】子任务 2：筛选与联想增强 · PRD

> 状态：草稿，待用户过目后 `task.py create "筛选与联想增强" --slug filter-suggest --parent 07-26-frontend-redesign` 并转正。
> 依赖：子任务 1（07-26-front-base）已交付的筛选栏 / 搜索框 / use-filter-params。

## Goal

给前台补上两块设计稿能力：**筛选栏作者区**（artist 维度筛选）与**搜索联想下拉**（前缀匹配 + 连带链 + 废弃提示），前后端一起交付。

## Requirements

### R1 后端：作者列表接口
- `GET /api/artists`（或 `GET /api/tags?category=artist` 复用现有——设计决策见 design 草稿）：返回 artist 分类标签及 post_count，按计数降序；供筛选栏作者区与作者视图头部用。
- 复用倾向：现有 `GET /api/tags` 已支持 `category=artist&order=count`，若字段够用则**不加新端点**，前端直接用（零后端改动）。需确认：作者视图头部要的"统计行"（图片数/最早/最近）是否本期做——设计稿有，如做需扩展 tag 详情接口。

### R2 后端：标签联想接口
- `GET /api/tags/suggest?prefix=<q>&limit=10`：前缀匹配（大小写不敏感），返回：name、category、post_count、is_deprecated、连带链预览（该标签的直接 consequents，如 miku → vocaloid）。
- 排序：post_count 降序；废弃标签排最后且带标记。
- 现有 `GET /api/tags?search=` 是子串匹配且无连带链——联想需要前缀语义 + 连带预览，判断是否新端点或扩展现有（design 草稿细化）。
- pytest：前缀命中/大小写/废弃标记/连带链/空前缀 422 或空数组（定一种）。

### R3 前端：筛选栏作者区
- rail 在"标签"区上方加"作者 ARTISTS"区：琥珀圆点 + mono 名称 + 计数（设计稿首页第 1 屏样式）；点击 = toggle 进 `?tags=`（作者就是标签，复用 use-filter-params 现有写路径）。
- 折叠图标条相应加"作者"图标（lucide User/Palette 按对照表）。
- 移动筛选抽屉同步出现作者区（rail 区块继续单份复用）。

### R4 前端：搜索联想下拉
- search-box 输入 ≥1 字符防抖 150ms 调 suggest；下拉玻璃层（glass-pop）按 final-states.dc.html 第 1 屏：匹配前缀高亮、分类色圆点、计数、连带补全提示（"miku 连带补全 → vocaloid"）、废弃行划线 + "已废弃 · 建议改用 X"（不阻断选择）、最近搜索（localStorage，最多 5 条）、↑↓/Enter 键盘导航 + Esc 关闭。
- 选中联想项 = 把该词填进输入框当前词位（空格 AND 语义保持）；Enter 提交行为不变。
- `useTagSuggest(prefix)` hook：防抖 150ms、staleTime 短、空前缀不发请求。

### R5 前端：作者视图头部
- 当 `?tags=` 恰好含一个 artist 分类标签时，标题行升级为作者头部（46px 琥珀图标 + mono 名称 + artist 徽章 + 图片计数；设计稿第 3 屏）；统计行有多少数据显示多少（不为此扩后端，除非 R1 决定扩）。

### 明确不做
- 星标/收藏、"只看已收藏"（父任务决策 3）。
- 管理面板任何页面；废弃标签的管理操作（子任务 3）。
- 搜索历史云端同步（localStorage 即可）。

## Acceptance Criteria（草稿）
- [ ] 作者区显示 artist 标签+计数，点击筛选生效，桌面/移动一致。
- [ ] 联想：输入前缀出下拉，键盘可完整操作，废弃/连带提示按稿呈现，防抖 150ms（网络面板验证）。
- [ ] 作者视图头部在单 artist 筛选时出现。
- [ ] 后端新/改接口 pytest 全绿；`npm run lint` + `tsc --noEmit` 全绿。
- [ ] 浏览器走查桌面 + 402 移动两档。
