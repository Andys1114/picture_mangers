# Implement — 交付 pending 迁移

## 前置确认

- [ ] `grep -rn fav_count backend/` 仅命中 `post.py:39` + 初始迁移 `:48`（审计已知；如有遗漏先清理）。
- [ ] `alembic upgrade head` 在当前代码上先跑通（基线绿）。
- [ ] `pytest -v` 基线绿（当前 11 passed）。

## 执行步骤（按序）

### S1 — model 改 `post.py`
- [ ] 删 `fav_count` 列（含行尾注释对齐）。
- [ ] 加 `duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), nullable=True)`，位置放在 `is_duplicate` 附近。
- [ ] 给 `is_duplicate` + `duplicate_of_id` 加注释：`is_duplicate` 是 fast-filter 便利布尔，`duplicate_of_id IS NOT NULL` 是权威去重信号。
- [ ] `__table_args__` 加 `Index("ix_posts_source_site_source_id", "source_site", "source_id", unique=True, sqlite_where=text("source_site IS NOT NULL AND source_id IS NOT NULL"))`。
- [ ] import 补 `ForeignKey, Index, text`。

### S2 — 手写迁移（不依赖 autogenerate）
- [ ] 在 `backend/` 下生成空 revision：`python -m alembic revision -m "align post schema: drop fav_count, add duplicate_of_id, add source partial unique index"`（记下 revision id 与 down_revision=`f3d99311f0cf`）。
- [ ] `upgrade()`：
  - batch drop `fav_count`。
  - batch add `duplicate_of_id`（`sa.Integer(), nullable=True`，FK `('duplicate_of_id',) → ('posts.id',)`, `ondelete='SET NULL'`）。
  - batch create_index `ix_posts_source_site_source_id`（`['source_site','source_id']`, unique=True, `sqlite_where=...`）。
- [ ] `downgrade()` 逆序：drop index、drop `duplicate_of_id`、recreate `fav_count`（`sa.Integer(), nullable=False, server_default='0'`）。
- [ ] 删掉模板里的占位 `pass`。

### S3 — 更新 schema 测试 `tests/test_schema.py`
- [ ] `EXPECTED_TABLES` 不变（仍 8 张）。
- [ ] 新增断言：`posts` 无 `fav_count` 列（`PRAGMA table_info(posts)` 不含）、有 `duplicate_of_id` 列、`sqlite_master` 含 `ix_posts_source_site_source_id` 且 SQL 含 `WHERE` 谓词。
- [ ] 新增 downgrade 用例：migrated DB 上 `command.downgrade(cfg, "base")`（或 `-1`）成功，再查 `fav_count` 回归、`duplicate_of_id`/索引消失。

### S4 — 验证
- [ ] `python -m alembic upgrade head`（干净 tmp DB 或测试 DB）成功。
- [ ] `python -m alembic downgrade -1` 成功、再 `upgrade head` 回到 head 成功。
- [ ] `python -m pytest -v` 全绿（在 `backend/` 下运行）。

## 验证命令

```bash
cd backend
grep -rn fav_count . --include="*.py"          # AC3：仅迁移 drop 语句/注释命中
python -m alembic upgrade head                 # AC1
python -m alembic downgrade -1 && python -m alembic upgrade head   # AC2 可逆
python -m pytest -v                            # AC4 全绿
```

## 风险点 / 回滚锚

- autogenerate 不可靠（部分索引谓词会丢）→ 全程手写 S2。
- 自引用 FK + batch：若 upgrade 报 FK 相关错，检查 env.py `render_as_batch=True` 与 `foreign_keys=ON` pragma（应已就位）。
- 回滚点：每步后 `alembic downgrade -1` 验证可逆；model 改动可用 `git checkout backend/app/models/post.py` 撤销。

## 完成闸（与 PRD AC 对齐）

- AC1 upgrade 后表结构三项变更到位。
- AC2 downgrade 可逆。
- AC3 grep 无 model/service/route 残留 `fav_count` 引用。
- AC4 pytest 全绿。
- AC5 `is_duplicate`/`duplicate_of_id` 注释与 spec 一致。
