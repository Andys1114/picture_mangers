# 标签 implication 写入侧 + tags 端点 — 技术设计

> 配套 `prd.md`。本切片实现 ADR-0001 的写入侧（物化闭包 + 防环 + 回填）+ 标签资源 CRUD 端点。读取侧（`search.py`）不动。

## 1. 模块边界

```
backend/app/services/tags.py      ← 新增：写入侧核心（闭包/防环/回填/打标签/CRUD 服务）
backend/app/api/tags.py           ← 新增：标签资源端点（GET 列表/tree/详情、POST、PATCH）
backend/app/schemas/tag.py        ← 新增：Pydantic 请求/响应模型
backend/app/api/__init__.py       ← 改：挂 tags router
backend/app/schemas/__init__.py   ← 视情况：导出 tag schemas
backend/tests/test_tags.py        ← 新增：端到端 + 单元
```

**不碰**：`services/search.py`（读取侧）、`models/`（schema 不变）、`alembic/`、`media.py`、`auth.py`、`config.py`、`db.py`。

层级守约：`tags.py` service 不导入 fastapi；`api/tags.py` route 薄（parse + 调 service + 返回 schema）。

## 2. 核心数据流

### 2.1 `tag_post(db, post_id, names)` —— 打标签 + 物化

```
tag_post(db, post_id, names: list[str]) -> list[Tag]
  │
  ├─ 1. 对每个 name：get_or_create Tag（post_count 初始 0）
  ├─ 2. 收集所有直接 tag_id 集合 direct = {A, ...}
  ├─ 3. closure = closure_of(db, direct)  # 递归 CTE 算整条连带闭包
  ├─ 4. 对 closure 中每个 tag_id：
  │      - 若 (post_id, tag_id) 不在 post_tags：插入 PostTag + 该 tag.post_count += 1
  │      - 若已存在：跳过（复合主键去重，幂等）
  └─ 5. db.commit(); 返回 closure 对应 Tag 列表
```

**幂等性**：PostTag 复合主键天然去重，重复打同一标签不重复加 post_count（先查存在再 +1）。

### 2.2 `closure_of(db, tag_ids) -> set[int]` —— 递归 CTE 闭包（write-time only）

SQLAlchemy 2.0 CTE 写法（SQLite 递归 CTE）：

```python
from sqlalchemy import select, literal, true
from sqlalchemy.orm import Session
from app.models.tag import TagImplication

def closure_of(db: Session, tag_ids: list[int]) -> set[int]:
    """Return the full consequent closure of `tag_ids`: every tag reachable
    by following antecedent→consequent edges transitively. Write-time only
    (ADR-0001); reads never call this. Carries a visited guard in the
    application layer as belt-and-suspenders against pre-existing cycles.
    """
    if not tag_ids:
        return set()
    # Recursive CTE: seed = direct tag_ids; recurse via implications
    edges = select(TagImplication.antecedent_id, TagImplication.consequent_id).where(
        TagImplication.status == "active"
    ).cte("edges", recursive=True)
    seed = select(literal(1).label("x"))  # placeholder; real seed below
    # ... 标准 SQLAlchemy 递归 CTE 构造（union seed + join edges）
    # 返回 set[int]
```

**实现要点**：递归 CTE 的 seed 是 `tag_ids`，递归步是 `JOIN edges ON t.tag = edges.antecedent_id` 取 `consequent_id`。SQLite 支持 `WITH RECURSIVE`。visited 兜底：CTE 本身有递归终止（无新行即停），但应用层额外做 visited-set 防御已存在的环（ADR-0001 要求双保险）。

**注**：精确 SQL 构造在实现时参考 SQLAlchemy 2.0 递归 CTE 文档 + SQLite 语法。若 CTE 在测试环境有问题，退化方案是应用层 BFS（queue + visited set）——语义等价，性能在单用户量级可接受。**优先 CTE（spec 要求），BFS 仅作 fallback。**

### 2.3 `create_implication(db, antecedent_id, consequent_id)` —— 防环 + 回填

```
create_implication(db, antecedent_id, consequent_id) -> TagImplication
  │
  ├─ 1. 自环检查：antecedent == consequent → ConflictError 409
  ├─ 2. 反向可达性检查：consequent 能否到达 antecedent？
  │      reachable(db, consequent_id, antecedent_id) → True 则成环 → ConflictError 409
  ├─ 3. 插入 TagImplication(status="active")；unique 约束兜底重复
  ├─ 4. 回填：找所有 post_tags 中含 antecedent 的 post，对每个 post：
  │      - 算 antecedent 的新闭包（含新加的 consequent 及其下游）
  │      - 把 closure 中 post 还没有的 tag 补进 post_tags + post_count += 1
  └─ 5. db.commit(); return TagImplication
```

**reachable（反向可达性）**：从 `consequent_id` 出发沿 antecedent→consequent 边 BFS/DFS，看能否到 `antecedent_id`。若能，则加 antecedent→consequent 会成环。这步也可用递归 CTE（`closure_of(consequent_id)` 含 antecedent_id → 成环）。

**回填的正确性**：新建 A→B 后，所有打了 A 的 post 的 post_tags 必须含 B（及 B 的下游闭包）。回填用 `closure_of(A)` 重算每个受影响 post 的展开集，补差集。

### 2.4 `post_count` 维护

- `tag_post`：每个新插入的 (post_id, tag_id) 对应 tag 的 post_count += 1。
- `create_implication` 回填：每个补插的 post_tags 行对应 tag 的 post_count += 1。
- 不做减法（不删标签/不删 implication，黏语义）。post_count 永远 = post_tags 行数。

## 3. 端点设计（`api/tags.py`）

全部 `/api` 前缀，需认证（`Depends(get_current_user)`）。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/tags?search=&category=&order=count` | 标签列表，支持搜索补全 + 类别过滤 + post_count 排序 |
| GET | `/api/tags/tree` | implication 树：返回 antecedent→[consequents] 结构，供前端折叠展示 |
| GET | `/api/tags/{id}` | 单标签详情（id/name/category/post_count/is_deprecated） |
| POST | `/api/tags` | 新建标签 `{name, category}` → 201 |
| PATCH | `/api/tags/{id}` | 改 `{category?}` 和/或 `{name?}`（重命名，unique 约束兜底冲突） |

**不做**：`POST /api/tags/{id}/implications`（implication 创建只做服务）、`POST /api/posts/{id}/tags`（打标签只做服务）、`DELETE`（不做）。

## 4. Pydantic schemas（`schemas/tag.py`）

```python
class TagResponse(BaseModel):
    id: int
    name: str
    category: str
    post_count: int
    is_deprecated: bool

class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="general")  # general/character/copyright/artist/meta

class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = None

class TagListNode(BaseModel):
    """tree 节点：前因 + 它的直接后果列表。"""
    tag: TagResponse
    consequents: list[TagResponse]

class TagListResponse(BaseModel):
    data: list[TagResponse]
    meta: dict[str, Any] = Field(default_factory=dict)
```

## 5. 决策记录

| # | 决策 | 依据 |
|---|---|---|
| D1 | 打标签/implication **只做服务不做端点** | 用户拍板。切片4 抓取调服务函数不走 HTTP；打标签端点的真实用户是详情页编辑（切片6），那时接端点更自然。本切片聚焦物化闭环。 |
| D2 | 回填**同步** | 单用户图库量级，同步够；ADR/spec 没要求异步。回填在 create_implication 内当场做完。 |
| D3 | 不做删除 implication / DELETE tag | 黏语义（ADR-0001）：删 implication 不撤老图标签，语义重；删 tag CASCADE post_tags 会丢打标记录。本切片只做创建，删除留后续。 |
| D4 | 闭包用**递归 CTE**，应用层 visited 兜底 | spec 要求递归 CTE write-time only；ADR 要求双保险。fallback：BFS（语义等价，单用户量级可接受）。 |
| D5 | post_count **写时 ±1**，无懒重算 | spec 明确：post_tags 永远是展开集，post_count 永远准，写入时维护即可。 |
| D6 | 标签资源 CRUD 端点**做**（GET/POST/PATCH） | 父 design §6 明列；标签页 /tags 需要；GET 列表/补全切片4 也可能用。与"打标签端点"是两回事（前者是标签资源，后者是给 Post 打标签）。 |

## 6. 测试设计（`tests/test_tags.py`）

用 `client` fixture（tmp DB + migrated）+ `media.ingest` 造真 Post。需认证的端点先 `client.post("/api/auth/setup", ...)` 拿 cookie。

- `test_tag_post_materializes_closure` — AC1：建 A→B、B→C implications，给 post 打 A，post_tags 含 {A,B,C}，三标签 post_count 各 +1。
- `test_create_implication_cycle_rejected` — AC2：建 A→B 后，B→A 抛 ConflictError 409，TagImplication 行不增。
- `test_implication_backfill` — AC3：先打 A（无 implication），建 A→B 后回填，post_tags 含 B，B post_count +1。
- `test_post_count_accurate_and_idempotent` — AC5：重复打同一标签 post_count 不重复加；post_count = post_tags 行数。
- `test_tags_crud_endpoints` — AC6：POST/PATCH/GET 列表/GET 详情/GET tree，全 401 未登录 + 正常流程。
- `test_tag_post_end_to_end_with_search` — AC7：ingest Post → tag_post 打标签 → `GET /api/posts?tags=...` 搜到。
- `test_self_loop_rejected` — 自环 A→A 抛 ConflictError。

## 7. 兼容性 / 回滚

- **零 schema 变更**，无迁移风险。
- 新增端点：回滚只需删 `api/tags.py` router 挂载 + service 文件，DB 无影响。
- `seed_dev.py` 不改（它手插 PostTag 的占位逻辑可保留，或后续迁移到 `tag_post`——本切片不强求，seed 仍能用）。
- 读取侧（search.py）不动，向后兼容。

## 8. 风险

- **递归 CTE 在 SQLAlchemy 2.0 + SQLite 的写法**：需小心构造（recursive CTE 的 seed + union）。若实现卡壳，fallback 到应用层 BFS（语义等价，性能可接受）。design 优先 CTE（spec 要求），实现时若 CTE 有坑可退 BFS 并在 spec 记偏差。
- **回填性能**：单用户图库量级，回填扫所有含 antecedent 的 post 可接受。若未来量大，改异步（本切片不做）。
- **post_count 并发**：SQLite WAL 单写者，无并发写冲突。
