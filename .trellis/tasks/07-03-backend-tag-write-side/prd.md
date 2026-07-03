# 标签 implication 写入侧 + tags 端点 — PRD

> 父任务：`06-28-gallery-app`（design.md §3 搜索语法/§6 tags 端点）。父切片拆分中的 **切片 2 剩余**——切片 2 的搜索读取侧已交付（`services/search.py` 的 AND over post_tags），本切片补**写入侧 + 标签资源 CRUD**，让标签系统闭环。依赖切片 3（`services/media.py:ingest`，用于造真 Post 做端到端测试）。

## 1. Goal / 用户价值

把标签系统从「读取侧能搜、写入侧全靠 seed 手插」推进到「打标签 → 物化连带 → post_count 准 → 标签页有数据 → 标签可 CRUD」。交付后，切片 4（抓取）抓回的标签能经本切片的物化服务正确入库，标签页 `/tags` 有列表与 implication 树可展示。核心是 ADR-0001 的写入时物化闭包 + 防环 + 回填三件套。

## 2. 已确认事实（来自 codebase/spec/ADR 检查）

- **ADR-0001 钉死写入侧契约**（`docs/adr/0001-implication-materialized-at-write-time.md`）：打标签时当场算整条连带链（A→B→C）闭包一次性写进 `post_tags`；implication 后加时对现有打了前因的图做一次回填；删连带是"黏"的（不撤老图标签）；防环反向可达性检查成环 409、闭包带 visited 兜底。
- **spec `database-guidelines.md`**：`Tag.post_count` = `post_tags` 行数，写入时 ±1 维护；`PostTag` 复合主键 `(post_id, tag_id)`；`ondelete="CASCADE"`；`TagImplication` 有 `UniqueConstraint(antecedent_id, consequent_id)`；递归 CTE 仅 write-time。
- **spec `quality-guidelines.md`**：搜索本期 AND-only；防环 ConflictError 409；业务逻辑不在 route。
- **CONTEXT.md 连带词条**：前因自动带后果、前因保留可单独搜、写入时算实、两条不变量（回填+黏删除）。废弃标签与连带是两件独立的事。
- **模型已就位**（`app/models/tag.py`）：`Tag`(id/name unique/category/post_count/is_deprecated)、`PostTag`(post_id+tag_id PK)、`TagImplication`(antecedent_id/consequent_id/status/unique pair)。
- **读取侧已就位**（`app/services/search.py`）：`list_posts` 的 AND over post_tags、`tags_for_post` 返回展开集。本切片不改读取侧。
- **`media.ingest` 已就位**（切片 3）：可造真 Post 做端到端测试。
- **写入侧现状**：`services/` 无 tags 服务；`api/` 无 tags 路由；唯一 tag 写入在 `scripts/seed_dev.py` 手插 PostTag（占位）。
- **父 design.md §6 tags 端点**：`GET /api/tags`(列表+补全)、`GET /api/tags/tree`(implication 树)、`GET /api/tags/{id}`、`POST /api/tags`(新建)、`PATCH /api/tags/{id}`(改类别/重命名)。**未列 implication 创建端点、未列打标签端点**——两者均只做服务函数。

## 3. 范围

### In scope
- **`services/tags.py`**（新增）—— 标签写入侧核心服务：
  - `create_implication(db, antecedent_id, consequent_id)` —— 防环检查（反向可达性，成环抛 ConflictError 409）+ 插入 TagImplication + 回填现有前因 post（同步）。
  - `closure_of(db, tag_id) -> list[int]` —— 递归 CTE 算前因的整条连带闭包（write-time only，带 visited 兜底）。
  - `tag_post(db, post_id, names: list[str])` —— 给 Post 打标签：get-or-create Tag + 算闭包 + 一次性写 post_tags（展开集）+ post_count ±1。切片 4 抓取复用。
  - `list_tags(db, *, search, category, order)` / `get_tag` / `tag_tree` —— 读取辅助（供端点用）。
  - `create_tag(db, name, category)` / `update_tag(db, id, ...)` —— 标签资源 CRUD。
- **`api/tags.py`**（新增）—— 标签资源端点（父 design §6 列的）：`GET /api/tags`、`GET /api/tags/tree`、`GET /api/tags/{id}`、`POST /api/tags`、`PATCH /api/tags/{id}`。route 薄，调 service。
- **`schemas/tag.py`**（新增）—— Pydantic 请求/响应模型。
- **`tests/test_tags.py`**（新增）—— 端到端：media.ingest 造 Post → tag_post 打标签 → 物化 → search 验证；implication 创建+防环+回填；post_count 准；tags CRUD 端点。

### Out of scope
- 搜索读取侧改动（已就位）。
- **打标签端点**（给 Post 打标签的 HTTP 入口，如 `POST /api/posts/{id}/tags`）—— 只做服务函数，端点留切片 6 详情页编辑。
- **implication 创建端点** —— 只做服务函数，端点留后续（前端 implication 管理 UI 未定）。
- 删除 implication（黏语义，本切片只做创建）。
- `DELETE /api/tags/{id}`（父 design 未列；删标签会 CASCADE post_tags，语义重，留后续）。
- 抓取器、scraper（切片 4）。
- `PATCH /api/posts/{id}` 编辑端点（切片 6）。

## 4. 验收标准

- [ ] **AC1 — tag_post 物化闭包**：给 Post 打前因标签 A（存在 A→B→B→C 两条 implication），`post_tags` 含完整展开集 {A,B,C}；`tag.post_count` 对 A/B/C 各 +1。
- [ ] **AC2 — create_implication 防环**：建 A→B 后，再建 B→A 抛 ConflictError（409, code=conflict）；不写入 TagImplication 行。
- [ ] **AC3 — implication 后加回填**：先给 Post 打 A（无 implication），再建 A→B，回填后该 Post 的 post_tags 含 B；B 的 post_count +1。
- [ ] **AC4 — 黏删除不变量**：删除 implication（如本切片支持删）不撤老图标签——但本切片不做删除，此 AC 转为"不提供删除 implication 端点/服务"的显式 out-of-scope 声明（已记 §3）。
- [ ] **AC5 — post_count 准确**：打标签后 post_count = post_tags 行数；同一标签重复打不重复加（PostTag 复合主键去重）。
- [ ] **AC6 — tags CRUD 端点**：`POST /api/tags` 建标签、`PATCH` 改类别/重命名、`GET /api/tags?search=&category=&order=count` 列表、`GET /api/tags/{id}` 详情、`GET /api/tags/tree` 返回 implication 树结构。全部需认证（401 未登录）。
- [ ] **AC7 — 端到端**：media.ingest 造 Post → tag_post 打标签 → search.list_posts(tags=[...]) 能搜到该 Post（验证写入侧与读取侧闭环）。
- [ ] **AC8 — 回归**：`pytest -v` 全绿（原 31 + 新增 tags 测试）；spec 自查（无读时递归、防环 409、post_count 写时维护、业务逻辑不在 route）。

## 5. 约束

- 零 schema 变更（Tag/PostTag/TagImplication 字段全齐）。
- 遵守 ADR-0001 三不变量（写入时物化、回填、黏删除）。
- 防环：反向可达性检查，成环抛 ConflictError 409。
- 递归 CTE 仅 write-time（打标签 + 回填），读取侧不递归（search.py 已合规）。
- `from __future__ import annotations` + 类型注解 + ORM/Core 参数化查询。
- 业务逻辑不在 route（route 薄，调 service）。
- 新端点全部需认证（除已有 `/auth/status` 等，tags 端点都需 cookie）。

## 6. 开放问题

无（4 个边界问题已与用户敲定：打标签/implication 均只做服务不做端点；回填同步；不做删除 implication / DELETE tag）。
