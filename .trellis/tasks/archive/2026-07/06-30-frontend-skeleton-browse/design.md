# 前端骨架 + 浏览页瀑布流 — 技术设计（spec 合规修订版）

> 需求见 `prd.md`。本文描述后端最小端点 + 前端真接的边界、契约、数据流、取舍。

## 0. 阶段划分

- **阶段 B（后端最小端点）**：先补 posts/me/settings/media + search + dev seed，pytest 绿。
- **阶段 F（前端真接）**：脚手架 + 鉴权 + 浏览页，全部调真接口，零 mock。

## 1. 后端边界与契约

### 1.1 Session.safe_mode
- `app/models/user.py` `Session` 加 `safe_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)`。
- `app/services/auth.py` `create_session` 显式置 `safe_mode=True`（新会话默认安全）。
- Migration `add_session_safe_mode`：`batch_alter_table("sessions") add_column safe_mode Boolean nullable=False server_default="1"`；downgrade drop。render_as_batch 自动。

### 1.2 错误类型
- `app/services/errors.py` 加 `NotFoundError(AppError)`：`status_code=404, code="not_found"`。

### 1.3 Schemas（`app/schemas/post.py` 新增 + `auth.py` 加 MeResponse）
```python
# auth.py 追加
class MeResponse(BaseModel):
    id: int
    username: str
    safe_mode: bool

class UpdateSettingsRequest(BaseModel):
    safe_mode: bool

# post.py 新增
class TagResponse(BaseModel):
    id: int
    name: str
    category: str
    post_count: int

class PostSummaryResponse(BaseModel):
    id: int
    preview_path: str
    width: int
    height: int
    rating: str
    is_animated: bool
    favorite: bool = False   # 本期固定 False；favorites 真接口 #8 再算

class PostDetailResponse(PostSummaryResponse):
    file_path: str
    thumb_path: str
    source_site: str | None = None
    source_url: str | None = None
    md5: str
    created_at: datetime
    tags: list[TagResponse]

class PageMeta(BaseModel):
    page: int
    total: int

class PostListResponse(BaseModel):
    data: list[PostSummaryResponse]
    meta: PageMeta
```

### 1.4 Deps
- `app/deps.py` 加 `get_current_session(request, db) -> Session`：取 cookie token → `auth.get_session_row(db, token)`，None → `UnauthorizedError`。`auth.py` 加 `get_session_row(db, token) -> SessionRow | None`（复用 validate 逻辑但返回 row）。

### 1.5 Services（`app/services/search.py` 新增）
```python
def list_posts(db, *, tags: list[str], safe_mode: bool, page: int, limit: int, order: str = "id") -> tuple[list[Post], int]:
    stmt = select(Post).where(Post.duplicate_of_id.is_(None))
    # rating: safe_mode 注入 safe；否则不限定（本期前端不暴露 rating override，safe_mode 即权威）
    if safe_mode:
        stmt = stmt.where(Post.rating == "safe")
    # tags AND over post_tags（implication 已写入算实，直接匹配）
    for t in tags:
        if not t: continue
        stmt = stmt.where(
            Post.id.in_(select(PostTag.post_id).join(Tag, PostTag.tag_id == Tag.id).where(Tag.name == t))
        )
    # order
    stmt = stmt.order_by(Post.id.desc() if order != "random" else func.random())
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.offset((page-1)*limit).limit(limit)).scalars().all()
    return rows, total

def get_post(db, post_id) -> Post:  # raise NotFoundError
def tags_for_post(db, post_id) -> list[Tag]:
```
> 注：`order=random` 用 `func.random()`（SQLite）；本期前端默认 `order=id`，random 留接口但 #6 才用。

### 1.6 Routes（`app/api/posts.py` 新增 + `auth.py` 加 me/settings）
- `auth.py`：`/me` 改返 `MeResponse`（用 `get_current_session` 读 safe_mode）；新增 `PATCH /me/settings`（`UpdateSettingsRequest` → 更新 session.safe_mode → 返 `MeResponse`）。
- `posts.py`：router prefix `/posts`，tags `["posts"]`。
  - `GET /`：query `tags:str=""`, `page:int=1`, `limit:int=40`, `order:str="id"`；dep `get_current_session` 拿 safe_mode；调 `search.list_posts`；映射 `PostListResponse`。
  - `GET /{id}`：dep `get_current_user`；调 `search.get_post` + `tags_for_post`；映射 `PostDetailResponse`；缺失 `NotFoundError`。
- `api/__init__.py` 挂 posts router。

### 1.7 静态媒体
- `main.py`：`from fastapi.staticfiles import StaticFiles`；启动前 `settings.media_path.mkdir(parents=True, exist_ok=True)`；`app.mount("/media", StaticFiles(directory=str(settings.media_path)), name="media")`。

### 1.8 Dev seed（`backend/scripts/seed_dev.py`）
- 幂等：无 user 则建 `admin/pw12345678`；已有则跳过。
- 生成 ~12 条 Post：手写最小 PNG 字节（`zlib` + `struct`，纯色 200×300~800×600 变尺寸），写 `media/posts/{id}/{original,preview,thumb}.png`；rating 分布（多数 safe、几条 questionable/explicit）；打 2-3 个真 Tag + PostTag（含一组 implication 示例：miku→vocaloid，验证 AND 命中展开集）。`md5` 用文件字节算。
- dev-only，`python -m scripts.seed_dev`（cwd=backend/）；不进 pytest。

## 2. 前端边界与契约

### 2.1 目录（遵循 `directory-structure.md`）
```
frontend/
├── app/
│   ├── layout.tsx              根：Providers + Toaster + <html className="dark">
│   ├── providers.tsx           'use client'：QueryClientProvider + MeProvider(useMe)
│   ├── middleware.ts           cookie 门 → /login?next=
│   ├── setup/page.tsx / login/page.tsx / settings/page.tsx
│   └── (protected)/{layout.tsx, page.tsx}
├── components/{ui, browse, common}/
├── hooks/{useMe,useSetup,useLogin,useLogout,useInfinitePosts,useUpdateSafeMode}.ts
├── lib/{api,types,queryClient}.ts
└── styles/globals.css, next.config.ts, components.json, ...
```

### 2.2 lib/types.ts（镜像后端，snake_case 直配，零漂移）
```ts
export type Rating='safe'|'questionable'|'explicit';
export type TagCategory='general'|'character'|'copyright'|'artist'|'meta';
export interface User { id:number; username:string; }
export interface Me { id:number; username:string; safe_mode:boolean; }
export interface Tag { id:number; name:string; category:TagCategory; post_count:number; }
export interface PostSummary { id:number; preview_path:string; width:number; height:number; rating:Rating; is_animated:boolean; favorite:boolean; }
export interface PostDetail extends PostSummary { file_path:string; thumb_path:string; source_site:string|null; source_url:string|null; md5:string; created_at:string; tags:Tag[]; }
export interface PageMeta { page:number; total:number; }
export interface Paginated<T> { data:T[]; meta:PageMeta; }
export interface ApiError { error:{ code:string; message:string; } }
```

### 2.3 lib/api.ts
- `request<T>(path, init?)`：`fetch(path, {credentials:'include', ...init})`；非 2xx 解 `ApiError` 抛 `Error`（401 由调用方/hook 处理）；2xx 解 `{data,meta}` 或裸体。
- `api.status/setup/login/logout/me`、`api.updateSettings(safe_mode)`、`api.listPosts({page,limit,tags,order})`、`api.getPost(id)`。
- **无 mock 接缝**——`listPosts` 直接 `request<Paginated<PostSummary>>('/api/posts?...')`。

### 2.4 lib/queryClient.ts
- key factory：`meKey=['me']`、`postsKey({tags,order})=['posts',{tags,order}]`、`postKey(id)=['post',id]`。

### 2.5 Hooks
- `useMe`：`useQuery(meKey, api.me)`；401 → data undefined（providers 据此跳 login）。
- `useSetup/useLogin`：`useMutation` → 成功 `invalidate(meKey)` + router 跳转。
- `useLogout`：`useMutation` → `queryClient.clear()` + 跳 `/login`。
- `useInfinitePosts({tags,order})`：`useInfiniteQuery`，`queryFn: ({pageParam}) => api.listPosts({page:pageParam, tags, order, limit:40})`，`getNextPageParam: last => last.meta.page < ceil(total/limit) ? page+1 : undefined`，`initialPageParam:1`。
- `useUpdateSafeMode`：`useMutation(api.updateSettings)`，**乐观**：`onMutate` 改 me 缓存 `safe_mode` + `invalidate(postsKey)`；`onError` 回滚。spec 要求服务端权威，故乐观仅是 UI 即时反馈，真相以 `onSuccess` 重取 `/me` 为准。

### 2.6 组件
- `topbar.tsx`：`backdrop-blur` + 半透明表面 + border；滚动监听切 opacity/translate；hover/置顶复现。
- `search-box.tsx`：input + submit → `router.replace('/?tags=...')`（URL 状态，spec 要求搜索入 URL）。
- `safe-mode-toggle.tsx`：盾牌图标 Button，调 `useUpdateSafeMode`；读 `useMe().data?.safe_mode` 渲染态。
- `post-card.tsx`：`break-inside:avoid`；`<img>` 带 `width/height`（防 CLS）+ `alt`；hover 浮 ★（本地乐观翻转，TODO #8 真接口）+ 分级色块（右下，`ratingColor(rating)`）。
- `masonry-grid.tsx`：`columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-1`；底部 sentinel + IntersectionObserver → `fetchNextPage`；loading `<Skeleton>`。
- `tag-drawer.tsx`：Sheet 壳，空态「标签数据待 #7 接入」。
- `(protected)/page.tsx`：`useSearchParams` 读 `tags` → `useInfinitePosts` → MasonryGrid；空态文案。

### 2.7 鉴权流（真）
1. `middleware.ts`：matcher 排除 `/login`、`/setup`、`/_next`、`/media`、`/api`；受保护路由无 `gallery_session` cookie → redirect `/login?next=pathname`。
2. `/login`、`/setup` 客户端挂载调 `api.status()`：`setup_required` → 路由分流。
3. `providers.tsx`：`useMe()`；无数据（401）且不在 `/login|/setup` → `router.replace('/login')`。
4. 登录/向导成功 → `invalidate(meKey)` → providers 重取 → 进 `/`。

## 3. 数据流

- 鉴权：cookie 门(middleware) → status 分流(login/setup) → me 灌用户+safe_mode。
- 浏览：`/?tags=...` → `useInfinitePosts` → `GET /api/posts?tags=&page=` → 后端 `list_posts`（safe_mode 注入 safe、排除重复、AND）→ `{data,meta}` → MasonryGrid；滚动 → fetchNextPage。
- safe_mode：toggle → `PATCH /api/auth/me/settings` → 乐观改 me + `invalidate(posts)` → 列表按新 safe 重取。

## 4. 关键取舍

- **safe_mode 服务端权威**：字段上 Session，前端只读/透传，不本地持久化（spec 硬约束）。乐观仅为即时反馈，`onSuccess` 重取 `/me` 校正。
- **search 直接 post_tags AND**：implication 写入算实（ADR-0001），读时无递归 CTE。
- **dev seed 而非前端 mock**：seed 产真 DB 行 + 真静态文件，走真 API；不违反「禁前端 mock」。Pillow 没装，手写 PNG 字节。
- **favorite 本期固定 false**：favorites API 是 #8，★ 只做本地视觉翻转 + toast「已收藏（待 #8）」。
- **CSS columns 瀑布流**：零依赖，spec 指定。
- **不引入 Zustand**：spec 明确不需要；safe_mode 走 server state（TanStack Query 的 me 缓存）。

## 5. 兼容/回滚

- 后端：新 migration 可 downgrade；新增 router/service/schema 不动既有 auth 行为（`/me` 加字段，既有测试用子集断言不破）。回滚 = downgrade + 撤新文件。
- 前端：全在 `frontend/`，删目录即回滚，无后端影响。
- 联调：后端 8000 + 前端 3000，rewrite 同源。

## 6. 验证

- 后端：`cd backend && pytest -v`；手动 `python -m scripts.seed_dev` 后 `uvicorn app.main:app --reload`，curl `/api/posts`（带 cookie）。
- 前端：`cd frontend && npm run lint && npx tsc --noEmit && npm run build`；`npm run dev` 走 setup→登录→浏览→滚动→安全模式切换。
