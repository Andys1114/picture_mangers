# 筛选与联想增强 · 执行清单

按序执行；⛳ = 独立提交回滚点。约束沿用子任务 1：不跑 `next build`（dev 服务器互斥）、验证以 lint+tsc+pytest+浏览器走查为准。

## 阶段 A：后端 suggest

- [ ] A1 schemas + services.suggest_tags（ilike 转义、废弃排序、implies 批查）+ api 路由（注册在 `/{tag_id}` 之前）⛳
  - 验证：`cd backend && python -m pytest tests/test_tags.py -q`（新增 6 用例：前缀/大小写/废弃/implies/空 prefix/limit 422）

## 阶段 B：作者区 + 作者头部

- [ ] B1 `useTags` 参数化确认（category/order 透传）+ `rail-artists.tsx` 新区块；rail 与移动抽屉接入；折叠条加图标
- [ ] B2 `artist-header.tsx`：单 artist 筛选时替换标题行 ⛳
  - 验证：浏览器桌面+402 走查（seed 有 artist 分类标签吗？没有则先给 seed 补一个 artist 标签再走查——只改 seed 脚本数据，不动 schema）

## 阶段 C：联想下拉

- [ ] C1 `api.suggestTags` + `useTagSuggest`（150ms 防抖、空前缀不请求）
- [ ] C2 `search-suggest.tsx` 下拉 + `search-box.tsx` 改造（当前词替换、↑↓/Enter/Esc、外点关闭、最近搜索 localStorage）⛳
  - 验证：浏览器走查——输入前缀出下拉、键盘全流程、废弃/连带提示、防抖（网络面板确认 150ms 合并）

## 阶段 D：收口

- [ ] D1 全量：lint / tsc / pytest；grep 无星标收藏、无硬编码色值
- [ ] D2 桌面+移动走查对照设计稿；偏差修掉或记 notes（含"作者统计行不做"既定偏差）
- [ ] D3 spec 增量沉淀（如有新约定）；父任务 prd 勾选子任务 2

## 审查门

1. A1 pytest 绿再进 B。
2. C2 浏览器走查过再进 D。
