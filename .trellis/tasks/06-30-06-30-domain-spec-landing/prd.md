# 落地领域模型决策到规范与 ADR

> 本文档只描述**需求、约束与验收标准**。来源：2026-06-30 `/grill-with-docs` 会话敲定的 10 条领域模型决策。

---

## 1. 背景

`/grill-with-docs` 对现有规范做了一次 grilling，敲定了 10 条领域模型决策（单用户语义、标签连带/废弃、防环、计数、收藏、重复图、评级、连带时机、搜索、抓取去重）。决策已落进根目录 `CONTEXT.md`（中文术语表）。但实现侧的 `.trellis/spec/backend/` 规范与父 PRD `06-28-gallery-app/prd.md` 仍停留在旧表述，且与 grilling 结论存在三处直接冲突。本任务把决策落地到规范与 ADR，并消解冲突。

## 2. 目标

1. 为最关键、最难反悔的决策（连带"写入时算实"）建立 ADR。
2. 更新 `.trellis/spec/backend/database-guidelines.md`、`quality-guidelines.md` 以反映新决策。
3. 回改父 PRD `06-28-gallery-app/prd.md`，消解三处冲突。

## 3. 范围

**只改文档，不改代码、不动数据库迁移。** 模型字段变更（删 `Post.fav_count`、加 `Post.duplicate_of_id`、加来源唯一索引）只在本任务的规范里**记录为待办契约**，实际迁移留给后续实现子任务。

## 4. 验收标准

### AC1. ADR
- [ ] `docs/adr/0001-implication-materialized-at-write-time.md` 存在，按 ADR 模板写明：背景、决策（写入时算实连带闭包、post_tags 存展开集）、替代方案（读时递归 CTE）、后果（搜索无需递归、post_count 永远准、删连带是"黏"的、防环仍需）。

### AC2. database-guidelines.md
- [ ] "denormalized counters" 段：删除 `fav_count`；`post_count` 改为"= post_tags 行数、永远准、由改 post_tags 的服务维护"，去掉任何"懒重算/脏标记"表述。
- [ ] "递归 CTE" 段：从"用于搜索展开"改为"**仅写入时**算连带闭包（打标签 + 连带回填）"，并补"防环：写入前反向可达性检查（成环则 409）+ 闭包计算带已访问集合兜底"。
- [ ] 新增"抓取去重"小节：`(source_site, source_id)` 对非空来源部分唯一索引；md5 兜底走重复图流程。
- [ ] "重复图"小节：md5 精确跳过 + phash 异步算近似；`duplicate_of_id` 自引用外键 `ondelete=SET NULL`；主视图默认隐藏、可收藏。

### AC3. quality-guidelines.md
- [ ] 搜索语义：post_tags 上 AND（本期不含 NOT/OR/通配，留后续版本）；按入库时间倒序；评级隐式过滤（主视图默认 safe）。
- [ ] 评级取值 `safe/questionable/explicit`。
- [ ] 重复图主视图默认隐藏写入规范。

### AC4. 父 PRD 回改
- [ ] `F4`：搜索语法标注"本期仅 AND；NOT/OR/通配为后续版本"。
- [ ] `AC3`：同步标注本期仅 AND；并补一句连带机制为"写入时算实（非读时递归），行为上仍为递归展开"。
- [ ] `F7`：删除"`posts.fav_count` 冗余字段"相关表述。
- [ ] `AC6`：删除"posts.fav_count 正确维护"验收项。

## 5. 约束

- 文档语言：`CONTEXT.md`/ADR 用中文（用户偏好）；`.trellis/spec/backend/` 与父 PRD 沿用各自既有语言（spec 英文、PRD 中文），保持各文档内部一致。
- 不创建/修改任何 `.py` 或迁移文件。
