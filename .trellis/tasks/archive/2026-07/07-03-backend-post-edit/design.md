# post 编辑/删除/next — 技术设计

> 配套 `prd.md`。复用 tag_post 做加标签，补「移除标签」逻辑，加删除（级联+文件）、next 翻页。

## 1. 模块边界

```
backend/app/services/post_edit.py   ← 新增：update_post / delete_post / next_post
backend/app/api/posts.py            ← 改：加 PATCH/DELETE/next 端点
backend/app/schemas/post.py         ← 改：加 PostUpdateRequest / PostNextResponse
backend/tests/test_post_edit.py     ← 新增
```

**不碰**：`models/`、`alembic/`、`tags.py`（只调 tag_post）、`media.py`、`search.py`（只调 get_post）。

层级守约：`post_edit.py` service 不导入 fastapi；`api/posts.py` route 薄调 service。

## 2. 数据流

### 2.1 `update_post(db, post_id, *, tags=None, rating=None) -> Post`

全量替换标签集（若传 tags）+ 改 rating（若传）。

```
post = search.get_post(db, post_id)  # 404
if rating is not None:
    post.rating = rating
if tags is not None:
    current = { post_tags 的 tag_id 集合 }
    target_names = tags (list[str])
    target_tags = [get_or_create Tag(name) for name in target_names]
    target_ids = { tag.id }
    # 加：target - current → tag_post 加（复用物化闭包）
    #   但 tag_post 接受 names 一次性加全部闭包；这里只需加差集
    #   差集 names = [Tag.name for id in (target - current)]
    to_add = [name for tid, name in target if tid not in current]
    if to_add: tags.tag_post(db, post_id, to_add)  # 复用物化
    # 删：current - target → 删 post_tags 行 + post_count-1
    to_remove = current - target_ids
    for tid in to_remove:
        delete PostTag(post_id, tag_id=tid)
        Tag.post_count -= 1
db.commit(); db.refresh(post); return post
```

**关键**：`tag_post` 一次调用加多个标签并算闭包——这里只传差集 `to_add`，闭包正确展开（若 to_add 含前因 A→B，B 也会加）。删差集 `to_remove` 时要注意：**删除 implication 是黏的（不撤老图标签），但删除 post_tags 行是直接删**——这里删的是「这个 post 上的这个标签」，不影响 implication 关系本身。但要小心：删了 post_tags 行后，若该标签是某 implication 的 consequent，其他 post 上的不受影响（post_tags 是 per-post 的）。安全。

### 2.2 `delete_post(db, post_id) -> None`

```
post = search.get_post(db, post_id)  # 404
# 删物理文件（media/posts/{id}/）
post_dir = settings.media_path / "posts" / str(post_id)
if post_dir.exists(): shutil.rmtree(post_dir)
# 删 DB 行（级联 post_tags/favorite_items）
db.delete(post); db.commit()
```

级联由 ondelete=CASCADE 保证（post_tags/favorite_items 的 FK）。文件删除在 DB 删之前（若文件删失败、DB 未删，post 仍在但文件没了——比反过来「DB 删了文件留着」好，孤儿文件可清，孤儿 Post 指向不存在文件更糟）。

### 2.3 `next_post(db, post_id) -> {prev_id, next_id}`

全局 id desc 相邻（当前 search 默认排序）。

```
search.get_post(db, post_id)  # 404 校验
# next：比当前 id 小的最近一个（id desc 视图下「下一张」= 更早入库）
next_id = select(Post.id).where(Post.id < post_id, duplicate_of_id IS NULL)
          .order_by(Post.id.desc()).limit(1)
# prev：比当前 id 大的最近一个
prev_id = select(Post.id).where(Post.id > post_id, duplicate_of_id IS NULL)
          .order_by(Post.id.asc()).limit(1)
return {prev_id, next_id}
```

**不过滤 tags/safe_mode**：design §6 说「翻页上下文」，未提过滤；详情页翻页是浏览所有图的上下文，不是搜索结果内翻页。若后续要搜索内翻页，前端传 tags 参数扩展（本切片不做）。排重图（duplicate_of_id IS NOT NULL）仍排除——与列表视图一致。

## 3. 端点设计（`api/posts.py`）

| 方法 | 路径 | 说明 |
|---|---|---|
| PATCH | `/api/posts/{post_id}` | 改标签（全量）和/或分级 |
| DELETE | `/api/posts/{post_post_id}` | 删 post + 文件 |
| GET | `/api/posts/{post_id}/next` | 翻页上下文 |

全部 `Depends(get_current_user)`。

**路由顺序**：`/next` 必须在 `/{post_id}` 之前注册（否则 `next` 被当成 post_id）。当前 posts.py 已有 `/{post_id}` GET，加 `/next` GET 要在前。但 `/next` 是 `/posts/{post_id}/next`（带 post_id 参数），与 `/posts/{post_id}` 不同路径层级，FastAPI 能区分。仍注意注册顺序。

## 4. Pydantic schemas（`schemas/post.py`）

```python
class PostUpdateRequest(BaseModel):
    tags: list[str] | None = None      # 全量替换；None=不动
    rating: str | None = Field(default=None, pattern=r"^(safe|questionable|explicit)$")

class PostNextResponse(BaseModel):
    prev_id: int | None
    next_id: int | None
```

## 5. 决策记录

| # | 决策 | 依据 |
|---|---|---|
| D1 | 标签全量替换 | 用户拍板。「编辑标签」心智是完整新列表；前端无需算 add/remove；服务端算差集复用 tag_post。 |
| D2 | DELETE 删物理文件 | 避免孤儿文件堆积；文件删在 DB 删前（失败时 post 仍在可重试，反之孤儿 Post 指向不存在文件更糟）。 |
| D3 | next 全局 id desc 不过滤 | design §6 未提过滤；详情页翻页是全局浏览上下文。排重图（duplicate_of_id IS NOT NULL）仍排除，与列表一致。 |
| D4 | 删 post_tags 行直接删（不撤 implication） | implication 黏删除（ADR-0001）针对 implication 关系本身；删 post_tags 是 per-post 的，不影响其他 post 或 implication 关系。 |
| D5 | 补「移除标签」逻辑在 post_edit.py | 切片2剩余 tag_post 只加不删；全量替换需要删，补在 post_edit.py（删 post_tags + post_count-1），不污染 tags.py 的加法语义。 |

## 6. 测试设计（`tests/test_post_edit.py`）

用 `client` + `media.ingest` + `tags.tag_post` 造带标签的 post。

- `test_update_post_replace_tags`（AC1）：原 {a,b} → PATCH {tags:[b,c]} → {b,c}，post_count ±1。
- `test_update_post_rating`（AC2）：PATCH {rating:"explicit"} → 改；只传 rating 不动标签。
- `test_update_post_partial`（AC3）：只传 tags 或只传 rating。
- `test_delete_post_cascade_and_files`（AC4）：删 → post 行删、post_tags/favorite_items 级联、目录删；404 不存在。
- `test_next_post`（AC5）：3 个 post，中间的 next 返回相邻；首尾 null。
- `test_edit_requires_auth`（AC6）：PATCH/DELETE/next 全 401。

## 7. 兼容性 / 回滚

- 零 schema 变更，无迁移风险。
- 新增端点：回滚删 post_edit.py + posts.py 的端点 + schemas，DB 无影响。
- 不改 tag_post/search/get_post，向后兼容。

## 8. 风险

- **全量替换的物化正确性**：删差集后，若删的标签是某 implication 的 consequent，加的标签是 antecedent，闭包要重算吗？不需要——tag_post(to_add) 会算 to_add 的闭包（含其 consequent），删 to_remove 只删指定 tag_id 不删其 consequent（consequent 若被其他保留标签的闭包带来仍保留）。但要测：删 antecedent 后其 consequent 是否该撤？按 ADR 黏语义，post_tags 删指定行，consequent 若由其他路径带来则保留。**测试覆盖此场景**。
- **删文件失败**：rmtree 失败抛异常，DB 未删，post 仍在但部分文件可能已删。可接受（重试或手动清理）。不做复杂补偿。
