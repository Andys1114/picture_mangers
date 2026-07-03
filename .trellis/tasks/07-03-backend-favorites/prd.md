# 收藏夹 F7 (favorites 端点) — PRD

> 父任务：`06-28-gallery-app`（PRD F7 + design.md §6 favorites 端点）。纯后端切片，表已建，只缺逻辑+端点+schemas。

## 1. Goal / 用户价值

把收藏夹从「表建好了、无端点」推进到「能建夹/加图/移图/调序/星标」。交付后，前端收藏 UI（切片 8）和详情页星标按钮（切片 6）有后端可调。核心是默认收藏夹语义：星标 = 加入/移出默认夹（toggle），一张图可同时在默认夹和其他命名夹。

## 2. 已确认事实（来自 codebase/spec/CONTEXT）

- **模型已就位**（`app/models/favorite.py`）：`Favorite`(id, name, TimestampMixin)、`FavoriteItem`(favorite_id+post_id 复合PK, position default=0)。复合 PK 天然防同图重复加入同一夹。
- **父 PRD F7**：多个收藏夹(像播放列表)、position 排序、系统自动维护**默认收藏夹**、星标=加入/移出默认夹、**不统计收藏次数**(无 fav_count，通过 favorite_items 成员判断)。
- **CONTEXT.md**：默认收藏夹承载星标动作；一张图可同时存在于默认夹和命名夹；收藏动作不统计次数。
- **spec `quality-guidelines.md`**：禁 fav_count、业务逻辑不在 route、AppError 子类带 stable code、类型注解+future annotations。
- **spec `database-guidelines.md`**：复合主键、ondelete CASCADE、ORM/Core 参数化查询。
- **父 design.md §6 favorites 端点**：GET 列表、POST 新建、GET 详情(含 posts)、POST 加项、DELETE 移项、PATCH 调序。
- **复用**：auth(get_current_user)、db(get_db)、errors(NotFoundError/ConflictError)、search.get_post(校验 post 存在)。

## 3. 范围

### In scope
- **`services/favorites.py`**：`create_favorite` / `get_favorite` / `list_favorites` / `add_item`(末尾 position) / `remove_item` / `reorder_item` / `get_or_create_default`(懒创建默认夹) / `toggle_star`(星标 toggle，操作默认夹)。
- **`api/favorites.py`**：父 design §6 的 6 端点 + **`POST /api/posts/{id}/favorite` 星标 toggle**（PRD F7 语义的必要补充，返回 `{favorited: bool}`）。
- **`schemas/favorite.py`**：FavoriteResponse / FavoriteCreateRequest / FavoriteDetailResponse(含 posts) / FavoriteItemReorderRequest / StarToggleResponse。
- **`tests/test_favorites.py`**：端到端（media.ingest 造 Post + 收藏夹 CRUD + 星标 toggle + 调序 + 401）。

### Out of scope
- 前端收藏 UI（切片 8）。
- post 编辑/删除/next 端点（切片 6 后端）。
- 导入/抓取任务调度（切片 8）。
- `DELETE /api/favorites/{id}`（删夹，父 design §6 未列，级联删 items 语义重，留后续）。

## 4. 验收标准

- [ ] **AC1 — 收藏夹 CRUD**：`POST /api/favorites` 建夹、`GET /api/favorites` 列表(精简不含 posts)、`GET /api/favorites/{id}` 详情(含 posts)。全部需认证(401 未登录)。
- [ ] **AC2 — 加项/移项**：`POST /api/favorites/{id}/items {post_id}` 加图(position 自动末尾 max+1)、`DELETE /api/favorites/{id}/items/{post_id}` 移图。复合 PK 去重(重复加入同夹不报错，幂等或 409)。
- [ ] **AC3 — 调序**：`PATCH /api/favorites/{id}/items/{post_id} {position}` 改 position。
- [ ] **AC4 — 星标 toggle**：`POST /api/posts/{id}/favorite` toggle 默认夹成员——首次加入返回 `{favorited:true}`、再次移出返回 `{favorited:false}`。默认夹懒创建(首次星标时建)。
- [ ] **AC5 — 默认夹语义**：一张图可同时在默认夹(星标)和命名夹(加入)，两者独立。星标只操作默认夹。
- [ ] **AC6 — 无 fav_count**：无任何收藏次数字段/逻辑；是否收藏通过 favorite_items 成员判断。
- [ ] **AC7 — 校验**：加项时 post 不存在 → 404；操作不存在的收藏夹 → 404。
- [ ] **AC8 — 回归**：`pytest -v` 全绿(原 46 + 新增 favorites 测试)；spec 自查(无 fav_count、route 薄调 service、零 schema 变更)。

## 5. 约束

- 零 schema 变更（Favorite/FavoriteItem 字段全齐）。
- 无 fav_count（spec 硬约束）。
- 默认夹懒创建（首次星标时建，name 用约定常量如 "★ 默认" 或 "default"）。
- position 加项自动末尾(max+1，空夹则 0)。
- `from __future__ import annotations` + 类型注解 + 业务逻辑不在 route + 全部端点需认证。

## 6. 开放问题

无（4 个边界问题已敲定：星标单独 toggle 端点；默认夹懒创建；position 末尾 max+1；GET 列表精简不含 posts）。
