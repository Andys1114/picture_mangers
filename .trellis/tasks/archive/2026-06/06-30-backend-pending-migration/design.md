# Design — 交付 pending 迁移

## 范围回顾

PRD 三项 schema 变更（drop `Post.fav_count` / add `Post.duplicate_of_id` / add `Post(source_site, source_id)` 部分唯一索引），让 schema 从"初始迁移早于 grilling 决策"的中间态推到与 spec/CONTEXT/ADR-0001 完全对齐。不实现业务逻辑（搜索/重复图过滤），仅对齐 schema + 注释。

## 架构与边界

只动两层：
- **model 层** `backend/app/models/post.py`：删 `fav_count` 列、加 `duplicate_of_id` 列 + 注释、在 `__table_args__` 加部分唯一索引。
- **迁移层** `backend/alembic/versions/<rev>_pending_schema_align.py`：在 `f3d99311f0cf` 之上新增一个 revision，`upgrade`/`downgrade` 完整。

不动 service/route/api/schemas（审计已确认无代码依赖 `fav_count`；`duplicate_of_id` 本任务只建列不消费）。

## 数据流 / 契约变更

- `Post.fav_count` 消失。favorite 状态仍由 `favorite_items` 成员关系派生（CONTEXT「收藏」词条），无任何代码读取该列。
- `Post.duplicate_of_id`：`Mapped[int | None]`，`ForeignKey("posts.id", ondelete="SET NULL")`，nullable。权威去重信号 = `duplicate_of_id IS NOT NULL`；`is_duplicate` 降级为 fast-filter 便利布尔。
- `Post(source_site, source_id)` 部分唯一索引：仅对两者都非空的行生效，防同一 site+id 重复抓取，DB 层兜底并发。

## 关键技术决策

### 1. 部分唯一索引在 SQLite + SQLAlchemy 的表达
SQLAlchemy 用 `Index("ix_posts_source_site_source_id", "source_site", "source_id", unique=True, sqlite_where=text("source_site IS NOT NULL AND source_id IS NOT NULL"))`。`sqlite_where` 是 SQLite 专用的部分索引谓词。`render_as_batch=True`（env.py 已设）下，Alembic 会把"加索引"放进 batch alter table，无特殊坑。

注意：autogenerate 默认**不**能可靠检测部分索引的谓词差异（这是 Alembic 的已知限制）。因此**手写迁移**而非依赖 autogenerate，并在升级后用 `sqlite_master` 断言索引存在且 SQL 含 `WHERE`。

### 2. 自引用 FK + batch mode
`duplicate_of_id` 指向 `posts.id`。SQLite ALTER 不能直接加带 FK 的列，但 `render_as_batch=True` 会重建表，FK 能正确落入。batch 重建时 SQLAlchemy 自动处理自引用（同表内 FK）。`ondelete="SET NULL"` 在 `foreign_keys=ON` pragma（env.py 已设）下生效。

### 3. 删列
`fav_count` 删除同样走 batch（重建表去掉该列）。downgrade 重建为 `Integer NOT NULL DEFAULT 0`，与初始迁移一致。

### 4. downgrade 可逆性
- drop `duplicate_of_id` 列（batch）。
- drop `ix_posts_source_site_source_id` 索引（batch）。
- recreate `fav_count`（`Integer, nullable=False, server_default="0"`，对齐初始迁移）。

downgrade 不需要回填数据（`fav_count` 本就是废弃的零值计数；`duplicate_of_id` 删除即丢失去重指向，但本任务尚未有数据消费它，可接受）。

## 兼容性 / 回滚

- 升级路径：`f3d99311f0cf` → 新 revision。`alembic upgrade head` 在干净 tmp DB 上必须成功。
- 回滚：`alembic downgrade -1` 必须无错回到初始迁移。
- 测试夹具 `conftest.py` 的 `client` fixture 跑 `command.upgrade(cfg, "head")`，会自动吃到新迁移，无需改夹具。

## 风险与对策

| 风险 | 对策 |
|---|---|
| autogenerate 漏掉部分索引谓词 | 手写迁移，不用 autogenerate |
| 现有 schema 测试断言写死 8 表结构 | 检查 `test_schema.py`，按需更新断言（加 `duplicate_of_id`/索引存在性） |
| 自引用 FK 在某些 SQLite 版本下 batch 重建异常 | 升级后断言 FK 存在；env 已开 `foreign_keys=ON` |
| `fav_count` 被某处隐性依赖（type/默认值） | grep `fav_count` 兜底（AC3），审计已知无 service/route 依赖 |

## 测试策略

- 复用 `conftest.py` 的 `client` fixture（tmp DB + `upgrade head`）。
- 升级后用 `sqlite3` 直查 `sqlite_master`：`posts` 无 `fav_count`、有 `duplicate_of_id`、有部分唯一索引且 SQL 含 `WHERE` 谓词。
- `alembic downgrade -1` 单测：在 migrated DB 上跑 downgrade，再查 `fav_count` 回归、`duplicate_of_id`/索引消失。
- `pytest -v` 全绿。
