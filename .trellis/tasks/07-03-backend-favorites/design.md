# 收藏夹 F7 — 技术设计

> 配套 `prd.md`。表已建，本切片补 service + 端点 + schemas。核心是默认夹懒创建 + 星标 toggle 语义。

## 1. 模块边界

```
backend/app/services/favorites.py   ← 新增：收藏夹逻辑（CRUD + 加移项 + 调序 + 默认夹 + 星标 toggle）
backend/app/api/favorites.py        ← 新增：6 个 favorites 端点 + POST /api/posts/{id}/favorite
backend/app/schemas/favorite.py     ← 新增：Pydantic 模型
backend/app/api/__init__.py         ← 改：挂 favorites router
backend/app/api/posts.py            ← 改：挂 favorite toggle router（或单独挂，见 §3）
backend/tests/test_favorites.py     ← 新增：端到端
```

**不碰**：`models/`、`alembic/`、`media.py`、`tags.py`、`scrape.py`、`search.py`。

层级守约：`favorites.py` service 不导入 fastapi；`api/favorites.py` route 薄调 service。

## 2. 默认夹语义（核心）

**默认夹是「系统自动维护」的特殊收藏夹**（CONTEXT.md），承载星标动作：
- **懒创建**：首次星标时，若默认夹不存在则建（name 用常量 `DEFAULT_FAVORITE_NAME = "默认收藏"`，单用户无需唯一性约束之外的标识）。
- **星标 toggle**：`POST /api/posts/{id}/favorite` —— 若该 post 已在默认夹 → 移出（返 `{favorited:false}`）；未在 → 加入（返 `{favorited:true}`）。
- **独立于命名夹**：一张图可同时在默认夹(星标)和命名夹(手动加入)，两者互不影响（AC5）。

**为何懒创建而非 setup 时建**：单用户场景无并发；懒创建避免 setup 逻辑改动（auth.setup 在切片1 交付，不改）；首次星标才需要默认夹，无星标则不建。

## 3. 端点设计（`api/favorites.py` + posts 挂载）

全部 `/api` 前缀，需认证。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/favorites` | 列表（精简，不含 posts） |
| POST | `/api/favorites` | 新建 `{name}` → 201 |
| GET | `/api/favorites/{id}` | 详情（含 posts 列表） |
| POST | `/api/favorites/{id}/items` | 加项 `{post_id}` → position 自动末尾 |
| DELETE | `/api/favorites/{id}/items/{post_id}` | 移项 |
| PATCH | `/api/favorites/{id}/items/{post_id}` | 调序 `{position}` |
| POST | `/api/posts/{id}/favorite` | **星标 toggle**（操作默认夹）→ `{favorited:bool}` |

**星标端点挂载**：挂 `api/favorites.py` 的 router（prefix `/`），但路径是 `/posts/{post_id}/favorite`——为避免与 `api/posts.py` 的 `/posts/{post_id}` 路由冲突，favorites router 不用 `/posts` prefix，而是用绝对路径 `/posts/{post_id}/favorite`。或：在 `api/posts.py` 加这个端点调 favorites service。**推荐后者**（挂 posts.py，语义上星标是 post 上的动作），避免 router prefix 混乱。

## 4. Pydantic schemas（`schemas/favorite.py`）

```python
class FavoriteResponse(BaseModel):
    id: int
    name: str
    item_count: int  # 列表用精简计数，不含 posts

class FavoriteCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)

class FavoriteItemResponse(BaseModel):
    post_id: int
    position: int

class FavoriteDetailResponse(BaseModel):
    id: int
    name: str
    items: list[FavoriteItemResponse]  # 详情含 posts（post 摘要）

class FavoriteItemReorderRequest(BaseModel):
    position: int = Field(ge=0)

class StarToggleResponse(BaseModel):
    favorited: bool
```

## 5. service 数据流

### 5.1 `get_or_create_default(db) -> Favorite`
```
查 Favorite(name=DEFAULT_FAVORITE_NAME) → 命中返回；未命中建 + commit + refresh。
```

### 5.2 `toggle_star(db, post_id) -> bool`
```
default = get_or_create_default(db)
existing = FavoriteItem(favorite_id=default.id, post_id=post_id) 查
  命中 → delete + commit → return False
  未命中 → 校验 post 存在(search.get_post 404) + insert(position=末尾) + commit → return True
```

### 5.3 `add_item(db, favorite_id, post_id) -> FavoriteItem`
```
校验 favorite 存在(404) + post 存在(404)
position = max(items.position) + 1 或 0（空夹）
insert FavoriteItem（复合PK 冲突 → ConflictError 409 幂等拒绝重复加）
```

### 5.4 `reorder_item(db, favorite_id, post_id, position)`
```
查 item(404) → 直接赋 position → commit
（不做复杂重排/紧凑化，单用户量级，前端约束连续性）
```

## 6. 决策记录

| # | 决策 | 依据 |
|---|---|---|
| D1 | 星标单独 toggle 端点 `POST /api/posts/{id}/favorite` | 用户拍板。星标是高频单按钮动作，toggle 最贴合 UX；默认夹是内部概念，前端无需知其 id。 |
| D2 | 默认夹懒创建（首次星标时建） | 单用户无并发；避免改 setup 逻辑；无星标则不建。 |
| D3 | position 加项末尾 max+1，调序直接赋值 | 单用户量级，不做复杂重排/紧凑化。 |
| D4 | GET 列表精简（item_count，不含 posts） | 列表 payload 小；详情才含 posts（父 design §6 约定）。 |
| D5 | 星标端点挂 `api/posts.py`（非 favorites router） | 语义上星标是 post 上的动作；避免 favorites router 用 `/posts` prefix 与 posts 路由冲突。 |
| D6 | 重复加入同夹 → ConflictError 409 | 复合PK 去重；幂等拒绝而非静默，让前端知道。 |
| D7 | 不做 DELETE 收藏夹 | 父 design §6 未列；级联删 items 语义重，留后续。 |

## 7. 测试设计（`tests/test_favorites.py`）

用 `client` fixture + `media.ingest` 造 Post + setup 拿 cookie。

- `test_favorites_crud`（AC1）：POST 建 / GET 列表(精简) / GET 详情(含 items)。401 未登录。
- `test_add_remove_item`（AC2）：加项 position 自动末尾 / 移项 / 重复加 409。
- `test_reorder_item`（AC3）：PATCH 调序。
- `test_star_toggle`（AC4）：首次星标 favorited=true / 再次 false / 默认夹懒创建。
- `test_default_independent_of_named`（AC5）：星标默认夹 + 加入命名夹，两者独立。
- `test_no_fav_count`（AC6）：响应无收藏次数字段。
- `test_404_on_missing`（AC7）：加项 post 不存在 404 / 操作不存在的夹 404。

## 8. 兼容性 / 回滚

- 零 schema 变更，无迁移风险。
- 新增端点：回滚删 `api/favorites.py` + 挂载 + service + schemas，DB 无影响。
- `PostSummaryResponse.favorite` 字段（posts.py 现硬编码 False）—— 本切片后可由 favorites service 查成员回填，但属 posts 列表响应改动，**本切片不改 posts.py 响应**（留后续，避免范围蔓延）。

## 9. 风险

- **position 空洞**：调序/移项后 position 可能不连续（如 0,1,3）。单用户量级可接受，前端按 position 排序即可；不做紧凑化。
- **默认夹 name 冲突**：若用户手动建了同名「默认收藏」夹，星标会复用它。可接受（单用户，语义一致）。或用 is_default 标志位——但 schema 无此字段，不改 schema 约束下用 name 约定。
