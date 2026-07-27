# 筛选与联想增强

父任务：`07-26-frontend-redesign`（子任务 2/7）。
设计稿：`docs/design/pm-gallery-redesign/README.md` 前台第 1、3 屏 + `final-states.dc.html` 搜索联想屏。
依赖：子任务 1（已归档 `07-26-front-base`）交付的筛选栏 / 搜索框 / `use-filter-params`。

## Goal

给前台补上设计稿的两块能力：**筛选栏作者区**（artist 维度筛选 + 作者视图头部）与**搜索联想下拉**（前缀匹配 + 连带链 + 废弃提示），前后端一起交付。

## Requirements

### R1 作者数据（零后端新端点）
- 作者列表直接用现有 `GET /api/tags?category=artist&order=count`（name/category/post_count/is_deprecated 字段够用）。
- 作者视图头部只展示标签数据已有的信息（名称 + 图片计数 + artist 徽章）；设计稿里的"最早/最近入库"统计行**本期不做**（需要扩接口，记入偏差）。

### R2 后端：标签联想接口
- 新增 `GET /api/tags/suggest?prefix=<q>&limit=<n>`（limit 缺省 10、上限 20）：
  - 前缀匹配，大小写不敏感；空/纯空白 prefix 返回空数组（200）。
  - 返回项：`name`、`category`、`post_count`、`is_deprecated`、`implies`（该标签直接后果标签名数组，如 miku → ["vocaloid"]）。
  - 排序：未废弃在前，组内 post_count 降序；同数按 name。
- pytest：前缀命中 / 大小写不敏感 / 废弃排序与标记 / implies 链 / 空 prefix 空数组 / limit 上限。

### R3 前端：筛选栏作者区
- rail"标签"区上方加"作者 ARTISTS"区：琥珀圆点 + mono 名称 + 计数；点击 = toggle 进 `?tags=`（作者即标签，复用 use-filter-params）。
- 折叠图标条加作者图标；移动筛选抽屉同步出现作者区（区块继续单份复用）。

### R4 前端：搜索联想下拉
- 输入 ≥1 字符防抖 150ms 调 suggest；glass-pop 下拉按 final-states 设计：前缀高亮、分类色、计数、连带补全提示（"连带补全 → vocaloid"）、废弃行划线 + "已废弃 · 建议改用"提示（不阻断选择）、最近搜索（localStorage ≤5 条，仅空输入时显示）、↑↓/Enter 键盘导航、Esc 关闭、点击外部关闭。
- 选中联想项 = 替换输入框**当前词**（空格 AND 语义不变）；Enter 无高亮项时按原样提交。
- `useTagSuggest(prefix)` hook：防抖 150ms、空前缀不发请求。

### R5 前端：作者视图头部
- `?tags=` 恰含一个 artist 分类标签时，标题行升级为作者头部（琥珀图标 + mono 名称 + artist 徽章 + 图片计数，设计稿第 3 屏样式，无统计行）。

### 明确不做
- 星标/收藏、"只看已收藏"（父任务决策 3）；管理面板（子任务 3+）；作者统计行扩接口；搜索历史云端化。

## Acceptance Criteria

- [ ] 作者区（桌面 rail + 移动抽屉）显示 artist 标签+计数，点击筛选生效。
- [ ] suggest 接口 pytest 六类用例全绿；空 prefix 与 limit 边界行为符合 R2。
- [ ] 联想下拉键盘可完整操作（↑↓/Enter/Esc），防抖 150ms，废弃/连带提示按稿呈现。
- [ ] 单 artist 筛选时出现作者头部。
- [ ] `npm run lint` + `tsc --noEmit` + 后端 pytest 全绿；浏览器走查桌面 1280 + 移动 402。
- [ ] 无星标/收藏 UI；组件内无硬编码色值。
