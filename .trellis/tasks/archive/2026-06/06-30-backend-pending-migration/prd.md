# 交付 pending 迁移：drop fav_count / add duplicate_of_id / add source 部分索引

## Goal

把后端 schema 从"初始迁移早于 grilling 决策"的中间态推到与新后端规范完全对齐：删除 `Post.fav_count`、新增 `Post.duplicate_of_id`、新增 `Post(source_site, source_id)` 部分唯一索引。让 schema 一次性兑现 spec/CONTEXT/ADR-0001 中的 domain field contract。

本任务由 `06-30-backend-spec-align`（仅修偏差 + 跟踪欠债）拆出，专门承载 spec 明确推迟给"后续子任务"的 schema 变更。待搜索/重复图功能落地前再激活实施。

## Background

spec `database-guidelines.md`「Duplicate Images (Post)」「Domain Field Contract (pending migration)」与 `quality-guidelines.md`「Domain Field Contract (pending migration)」「Forbidden Patterns」明确要求这三项 schema 变更，且把当前"初始迁移早于决策"的状态视为可接受的中间态——但要求"由后续子任务交付"。`CONTEXT.md` 同样记录：Post 无被收藏数字段、重复图通过 `duplicate_of_id` 指向原图、来源只记最早一个。

当前代码状态（确认事实）：
- `Post.fav_count` 仍存在于 `backend/app/models/post.py:39` 与初始迁移 `alembic/versions/f3d99311f0cf_initial_schema.py:48`，无 service/route 依赖它。
- `Post.duplicate_of_id` 缺失；`is_duplicate` 已存在（`post.py:36`）作为 fast-filter，但权威信号 `duplicate_of_id IS NOT NULL` 尚不可用。
- `Post(source_site, source_id)` 部分唯一索引缺失。

## Requirements

- **R1**：新增 Alembic 迁移（在 `f3d99311f0cf` 之上），含三项变更：
  - drop `Post.fav_count`（model + 迁移同步）。
  - add `Post.duplicate_of_id`：自引用 FK `ForeignKey("posts.id", ondelete="SET NULL")`，nullable；同步 model。
  - add `Post(source_site, source_id)` 部分唯一索引（仅对非空来源生效，SQLite 用 `WHERE source_site IS NOT NULL AND source_id IS NOT NULL` 等价条件）。
- **R2**：`is_duplicate` 注释明确为 fast-filter 便利、`duplicate_of_id IS NOT NULL` 为权威信号（与 spec 一致）。
- **R3**：迁移 downgrade 可逆（drop 索引、drop 列、可重建 `fav_count`）。
- **R4**：确认全 `backend/` 无任何代码依赖 `fav_count`（审计已知无 service/route 依赖；实施时再 grep 兜底）。

## Acceptance Criteria

- [ ] **AC1**：`alembic upgrade head` 在干净 tmp DB 上成功；落库后 `posts` 表无 `fav_count` 列、有 `duplicate_of_id` 列（nullable、自引用 FK、`ondelete SET NULL`）、有 `(source_site, source_id)` 部分唯一索引。
- [ ] **AC2**：`alembic downgrade -1` 可逆，不报错。
- [ ] **AC3**：`grep -rn fav_count backend/` 仅出现在新迁移的 drop 语句/注释中（如有），无 model/ service/ route 残留引用。
- [ ] **AC4**：`pytest -v`（在 `backend/` 下运行）全绿，含 schema 测试反映新结构。
- [ ] **AC5**：`post.py` 的 `is_duplicate` 与 `duplicate_of_id` 注释与 spec 一致（fast-filter vs 权威信号）。

## Out of Scope

- 搜索/评级/重复图过滤的业务逻辑实现（仅对齐 schema）。
- phash 异步计算、抓取/导入 pipeline。
- 前端。

## Open Questions

- 无（验收口径已由 spec/CONTEXT 锁定）。实施时若 SQLite 部分唯一索引语法与批处理模式有交互，在 design 阶段定。
