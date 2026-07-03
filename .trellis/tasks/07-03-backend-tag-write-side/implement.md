# 标签 implication 写入侧 + tags 端点 — 执行计划

> 配套 `prd.md` + `design.md`。按序执行，每步带校验门。

## 0. 前置（task.py start 前已完成的规划产物）
- [x] prd.md（8 条 AC，无开放问题）
- [x] design.md（8 节：边界/数据流/端点/schemas/决策/测试/回滚/风险）
- [x] implement.md（本文件）

## 1. schemas/tag.py —— Pydantic 模型

- [ ] **1.1** 新建 `backend/app/schemas/tag.py`：`TagResponse`、`TagCreateRequest`、`TagUpdateRequest`、`TagListNode`、`TagListResponse`（按 design §4）。
  - **校验门**：`python -c "from app.schemas.tag import TagResponse, TagCreateRequest"`。

## 2. services/tags.py —— 写入侧核心

- [ ] **2.1** 新建 `backend/app/services/tags.py`，先写读取辅助：`get_tag`、`list_tags(search, category, order)`、`tag_tree`（implication 树结构供端点）。
- [ ] **2.2** 写 `closure_of(db, tag_ids) -> set[int]`（递归 CTE，write-time only）。先试 CTE，卡壳 fallback BFS（design §8）。
- [ ] **2.3** 写 `tag_post(db, post_id, names) -> list[Tag]`：get-or-create + closure + 写 post_tags（去重）+ post_count ±1（design §2.1）。
- [ ] **2.4** 写 `create_implication(db, antecedent_id, consequent_id)`：自环检查 + 反向可达性防环 + 插入 + 回填（design §2.3）。
- [ ] **2.5** 写 `create_tag(db, name, category)`、`update_tag(db, id, name?, category?)`（CRUD 服务）。
  - **校验门**：`python -c "from app.services import tags; print(tags.tag_post, tags.create_implication, tags.closure_of, tags.list_tags)"`。

## 3. api/tags.py —— 标签资源端点

- [ ] **3.1** 新建 `backend/app/api/tags.py`：`GET /tags`、`GET /tags/tree`、`GET /tags/{id}`、`POST /tags`、`PATCH /tags/{id}`，全部 `Depends(get_current_user)`。
- [ ] **3.2** `backend/app/api/__init__.py`：挂 `tags.router`。
  - **校验门**：`python -c "from app.main import app; print([r.path for r in app.routes if '/tags' in r.path])"` 见 5 条 tags 路径。

## 4. tests/test_tags.py —— 端到端 + 单元

- [ ] **4.1** 新建 `backend/tests/test_tags.py`，fixture 用 `client` + `media.ingest` 造 Post + setup 拿 cookie。
- [ ] **4.2** `test_tag_post_materializes_closure`（AC1）。
- [ ] **4.3** `test_create_implication_cycle_rejected`（AC2）+ `test_self_loop_rejected`。
- [ ] **4.4** `test_implication_backfill`（AC3）。
- [ ] **4.5** `test_post_count_accurate_and_idempotent`（AC5）。
- [ ] **4.6** `test_tags_crud_endpoints`（AC6，含 401 未登录）。
- [ ] **4.7** `test_tag_post_end_to_end_with_search`（AC7）。
  - **校验门**：`cd backend && python -m pytest tests/test_tags.py -v` 全绿。

## 5. 全量回归 + spec 自查

- [ ] **5.1** `cd backend && python -m pytest -v` → 原 31 + 新 tags 测试全绿。
- [ ] **5.2** spec 自查：grep 确认 search.py 无读时递归改动、防环抛 ConflictError 409、post_count 写时维护、route 无业务逻辑、无 create_all/raw SQL。
- [ ] **5.3** 端到端冒烟（可选）：跑 seed + 手动调 tag_post 验证。

## 校验命令汇总

```bash
cd backend
python -m pytest -v                            # 全量（5.1）
python -m pytest tests/test_tags.py -v         # 仅 tags（4.7 后）
python -c "from app.main import app; print([r.path for r in app.routes if '/tags' in r.path])"  # 3.2
```

## 回滚点

- **步骤 1-2 后**：删 `schemas/tag.py` + `services/tags.py`，DB 无影响。
- **步骤 3 后**：删 `api/tags.py` + 取消 `__init__.py` 挂载，端点消失，DB 无影响。
- **全切片回滚**：`git revert` 本次提交，零 schema 变更，无迁移需反向。

## 风险点（来自 design §8）

- 递归 CTE 写法：卡壳 fallback BFS（语义等价），优先 CTE（spec 要求）。
- 回填性能：单用户量级可接受，未来改异步。
