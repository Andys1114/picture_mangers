# post 编辑/删除/next 端点 (切片6后端) — PRD

> 父任务：`06-28-gallery-app`（design.md §6 posts 端点）。详情页 lightbox（切片6）的后端依赖。复用切片2剩余 `tag_post` + `search`。

## 1. Goal / 用户价值

把 post 从「只读」推进到「可编辑可删除可翻页」。交付后，详情页 lightbox（切片6）能改标签/分级、删除、键盘 ←→ 翻页。核心是复用已交付的 `tag_post`（物化闭包）做编辑，不重写物化逻辑。

## 2. 已确认事实（来自 codebase/spec）

- **父 design.md §6 posts 端点**：`PATCH /api/posts/{id}`(改标签/分级)、`DELETE /api/posts/{id}`(删)、`GET /api/posts/{id}/next`(翻页上下文 上一/下一 id)。
- **复用已就位**：
  - `services/tags.py:tag_post(db, post_id, names)` —— 打标签 + 物化闭包 + post_count（切片2剩余）。
  - `services/search.py:get_post`(404) + `list_posts`(排序 id desc)。
  - `services/favorites.py` —— 删 post 时 favorite_items 级联（ondelete CASCADE）。
- **Post 模型**：`rating`、`ondelete="CASCADE"` 关联 post_tags/favorite_items。删 post 级联删关联。
- **spec**：业务逻辑不在 route、AppError 子类、类型注解、零 schema 变更。
- **现有 posts 端点**：GET 列表、GET 详情。本切片加 PATCH/DELETE/next。

## 3. 范围

### In scope
- **`PATCH /api/posts/{id}`** —— 全量替换标签集（传完整新列表，差集：加的调 tag_post、删的删 post_tags + post_count-1）+ 可选改 rating。部分更新（只传 rating 不传 tags 也行）。
- **`DELETE /api/posts/{id}`** —— 删 post（级联 post_tags/favorite_items）+ 删 media/posts/{id}/ 物理文件。
- **`GET /api/posts/{id}/next`** —— 全局 id desc 相邻，返回 `{prev_id, next_id}`（不过滤 tags/safe_mode，详情页翻页用）。
- **`services/post_edit.py`**：update_post / delete_post / next_post 服务函数。
- **`schemas/post.py`**：加 PostUpdateRequest、PostNextResponse。
- **`tests/test_post_edit.py`**。

### Out of scope
- 详情页 lightbox 前端（切片6 前端）。
- 批量编辑/删除。
- next 尊重 tags/safe_mode 过滤（design §6 未提，取最简全局相邻）。
- import 任务调度（切片8）。

## 4. 验收标准

- [ ] **AC1 — PATCH 全量替换标签**：post 原标签 {a,b}，PATCH `{tags:["b","c"]}` → post_tags = {b,c}（a 删、c 加），post_count 对应 ±1。物化闭包仍正确（c 若有 implication 也展开）。
- [ ] **AC2 — PATCH 改 rating**：`PATCH {rating:"explicit"}` → post.rating 更新；只传 rating 不动标签。
- [ ] **AC3 — PATCH 部分更新**：只传 tags 或只传 rating，未传字段不动。
- [ ] **AC4 — DELETE 删 post + 级联 + 文件**：DELETE 后 post 行删、post_tags/favorite_items 级联删、media/posts/{id}/ 目录删。404 不存在的 post。
- [ ] **AC5 — next 翻页上下文**：`GET /api/posts/{id}/next` 返回 `{prev_id, next_id}`（id desc 视图下的上一/下一）。首尾的 prev/next 为 null。
- [ ] **AC6 — 认证**：PATCH/DELETE/next 全部 401 未登录。
- [ ] **AC7 — 回归**：`pytest -v` 全绿（原 52 + 新增 post_edit 测试）；spec 自查（复用 tag_post 不重写、route 薄调 service、零 schema 变更）。

## 5. 约束

- 零 schema 变更。
- 复用 tag_post 物化逻辑（加标签），新增「移除标签」逻辑（删 post_tags + post_count-1，切片2剩余「只加不删」的补全）。
- next 全局 id desc 相邻，不过滤。
- `from __future__ import annotations` + 类型注解 + 业务逻辑不在 route + 全部需认证。

## 6. 开放问题

无（3 个边界问题已敲定：全量替换标签；DELETE 删物理文件；next 全局 id desc 不过滤）。
