# 对齐后端代码与新后端规范

## Goal

把现有后端代码与 commit `13665fa` 落地的后端规范（grilling 决策：删 `fav_count`、连带写入时算实、搜索 AND-only、重复图/抓取去重语义）对齐，消除代码与 spec/ADR 之间的矛盾，并决定 pending 迁移的交付边界。

## Background

后端 spec 在 `13665fa` 改动了 `database-guidelines.md` + `quality-guidelines.md`，并新增根目录 `CONTEXT.md` 与 `docs/adr/0001-implication-materialized-at-write-time.md`。完整审计后得到两类发现：

**确认事实（codebase 可验证）**：
- `backend/app/models/tag.py:44` 的 `TagImplication` docstring 写着 "Search expands the chain recursively" —— 这正是 ADR-0001 否决、`quality-guidelines.md` 列为 forbidden 的"读时递归搜索"语义。真实偏差。
- `Post.fav_count` 仍存在于 `backend/app/models/post.py:39` 与初始迁移 `alembic/versions/f3d99311f0cf_initial_schema.py:48`。spec 明确将其列为 forbidden 并要求"由后续子任务迁移删除"，但**当前没有任何 active task 跟踪**。目前无 service/route 依赖它。
- spec 要求但代码尚缺的字段/索引（均属 spec 明确推迟到"后续子任务"的 pending 项）：`Post.duplicate_of_id`（自引用 FK，`ondelete="SET NULL"`，nullable）、`Post(source_site, source_id)` 部分唯一索引。
- 符合规范的既有项（无需改）：`Post.rating` 默认 `safe`、`md5` 唯一、`phash` nullable、`ConflictError(409)` 已存在、`ix_post_tags_tag_id` 反查索引、关联表复合主键 + `ondelete="CASCADE"`、bcrypt cost=12、AppError envelope、`alembic.ini` URL 空且 ASCII-clean、env.py 运行时注入 URL + `render_as_batch` + WAL/FK pragmas。

## Requirements

- **R1（修正偏差）**：改写 `backend/app/models/tag.py:44` `TagImplication` docstring，使其反映 ADR-0001（连带写入时算实、读时不递归），消除与 spec/ADR 的直接语义矛盾。
- **R2（跟踪 pending 迁移，非本任务交付）**：创建独立子任务跟踪 spec 的 pending 迁移（drop `Post.fav_count` / add `Post.duplicate_of_id` / add `Post(source_site, source_id)` 部分唯一索引）。本任务**不**交付该迁移，仅保证 R1 落地 + 该欠债被显式跟踪。

## Acceptance Criteria

- [ ] **AC1**：`tag.py:44` docstring 不再含"读时递归展开"语义；改写后文案与 ADR-0001 + `quality-guidelines.md` 的 forbidden 条款一致，并引用 ADR-0001。
- [ ] **AC2**：grep 全 `backend/` 无残留与新 spec 直接矛盾的注释/docstring（pending 迁移相关的 `fav_count`/`duplicate_of_id`/source 索引除外，它们由独立子任务交付）。
- [ ] **AC3**：pending 迁移已落为独立 Trellis 子任务（task.py create 成功），其 PRD 含三项 schema 变更的验收口径，本任务可归档而不丢失该欠债。

## Out of Scope

- 实现搜索/评级/重复图过滤的业务逻辑（spec 将其列为后续里程碑功能，本任务仅对齐 schema/docstring，不写 service）。
- 抓取/导入 pipeline 实现。
- 前端任何改动。

## Open Questions

- 无（范围已定：仅修偏差 + 另立子任务跟踪迁移）。
