# post 编辑/删除/next — 执行计划

> 配套 `prd.md` + `design.md`。按序执行，每步带校验门。

## 0. 前置（task.py start 前已完成）
- [x] prd.md（7 条 AC，无开放问题）
- [x] design.md（8 节：边界/数据流3函数/端点/schemas/决策5条/测试6例/回滚/风险）
- [x] implement.md（本文件）

## 1. schemas/post.py 加 PostUpdateRequest / PostNextResponse

- [ ] **1.1** `backend/app/schemas/post.py` 加 `PostUpdateRequest`(tags?/rating? pattern) + `PostNextResponse`(prev_id?/next_id?)。
  - **校验门**：`python -c "from app.schemas.post import PostUpdateRequest, PostNextResponse"`。

## 2. services/post_edit.py

- [ ] **2.1** 新建 `backend/app/services/post_edit.py`：`update_post`（全量替换标签：差集加调 tag_post + 差集删删 post_tags + post_count-1；改 rating）。
- [ ] **2.2** `delete_post`（删物理文件 shutil.rmtree + db.delete post 级联）。
- [ ] **2.3** `next_post`（id desc 相邻，排重图，prev/next）。
  - **校验门**：`python -c "from app.services.post_edit import update_post, delete_post, next_post"`。

## 3. api/posts.py 加端点

- [ ] **3.1** `backend/app/api/posts.py` 加 `PATCH /{post_id}`、`DELETE /{post_id}`、`GET /{post_id}/next`，全部 `Depends(get_current_user)`，route 薄调 post_edit service。
  - **校验门**：`python -c "from app.main import app; print([r.path for r in app.routes if '/posts/' in r.path])"`。

## 4. tests/test_post_edit.py

- [ ] **4.1** 新建 `backend/tests/test_post_edit.py`，fixture 用 `client` + `media.ingest` + `tags.tag_post`。
- [ ] **4.2** `test_update_post_replace_tags`（AC1）。
- [ ] **4.3** `test_update_post_rating`（AC2）+ `test_update_post_partial`（AC3）。
- [ ] **4.4** `test_delete_post_cascade_and_files`（AC4）。
- [ ] **4.5** `test_next_post`（AC5）。
- [ ] **4.6** `test_edit_requires_auth`（AC6）。
  - **校验门**：`cd backend && python -m pytest tests/test_post_edit.py -v` 全绿。

## 5. 全量回归 + spec 自查

- [ ] **5.1** `cd backend && python -m pytest -v` → 原 52 + 新 post_edit 测试全绿。
- [ ] **5.2** spec 自查：复用 tag_post 未重写、route 薄调 service、零 schema 变更、业务逻辑不在 route。

## 校验命令汇总

```bash
cd backend
python -m pytest -v                                  # 全量（5.1）
python -m pytest tests/test_post_edit.py -v          # 仅 post_edit（4.6 后）
```

## 回滚点

- **步骤 1-2 后**：删 schemas 加的字段 + post_edit.py，DB 无影响。
- **步骤 3 后**：删 posts.py 的端点，端点消失。
- **全切片回滚**：`git revert`，零 schema 变更。

## 风险点（来自 design §8）

- 全量替换物化正确性（删 antecedent 后 consequent 撤留）——测试覆盖。
- 删文件失败——重试或手动清理，不做复杂补偿。
