# 收藏夹 F7 — 执行计划

> 配套 `prd.md` + `design.md`。按序执行，每步带校验门。

## 0. 前置（task.py start 前已完成）
- [x] prd.md（8 条 AC，无开放问题）
- [x] design.md（9 节：边界/默认夹语义/端点/schemas/数据流/决策/测试/回滚/风险）
- [x] implement.md（本文件）

## 1. schemas/favorite.py

- [ ] **1.1** 新建 `backend/app/schemas/favorite.py`：FavoriteResponse(含 item_count)、FavoriteCreateRequest、FavoriteItemResponse、FavoriteDetailResponse、FavoriteItemReorderRequest、StarToggleResponse（design §4）。
- [ ] **1.2** `backend/app/schemas/__init__.py` 导出。
  - **校验门**：`python -c "from app.schemas.favorite import FavoriteResponse, StarToggleResponse"`。

## 2. services/favorites.py

- [ ] **2.1** 新建 `backend/app/services/favorites.py`：`DEFAULT_FAVORITE_NAME` 常量 + `get_or_create_default`（懒创建）。
- [ ] **2.2** `create_favorite` / `get_favorite`(404) / `list_favorites`(精简 item_count)。
- [ ] **2.3** `add_item`（校验 post 404 + 末尾 position + 复合PK 冲突 409）/ `remove_item`(404) / `reorder_item`(404)。
- [ ] **2.4** `toggle_star(db, post_id) -> bool`（get_or_create_default + 查成员 + toggle）。
  - **校验门**：`python -c "from app.services.favorites import toggle_star, create_favorite, add_item"`。

## 3. api/favorites.py + posts 挂载

- [ ] **3.1** 新建 `backend/app/api/favorites.py`：6 个 favorites 端点（GET 列表/POST/GET 详情/POST 加项/DELETE 移项/PATCH 调序），全部 `Depends(get_current_user)`。
- [ ] **3.2** `backend/app/api/posts.py` 加 `POST /{post_id}/favorite` 端点调 `favorites.toggle_star`（design D5：挂 posts.py）。
- [ ] **3.3** `backend/app/api/__init__.py` 挂 favorites.router。
  - **校验门**：`python -c "from app.main import app; print([r.path for r in app.routes if 'favorite' in r.path or '/favorite' in r.path])"`。

## 4. tests/test_favorites.py

- [ ] **4.1** 新建 `backend/tests/test_favorites.py`，fixture 用 `client` + `media.ingest` 造 Post + setup 拿 cookie。
- [ ] **4.2** `test_favorites_crud`（AC1，含 401）。
- [ ] **4.3** `test_add_remove_item`（AC2，含 409 重复加）。
- [ ] **4.4** `test_reorder_item`（AC3）。
- [ ] **4.5** `test_star_toggle`（AC4，含默认夹懒创建）。
- [ ] **4.6** `test_default_independent_of_named`（AC5）。
- [ ] **4.7** `test_no_fav_count`（AC6）+ `test_404_on_missing`（AC7）。
  - **校验门**：`cd backend && python -m pytest tests/test_favorites.py -v` 全绿。

## 5. 全量回归 + spec 自查

- [ ] **5.1** `cd backend && python -m pytest -v` → 原 46 + 新 favorites 测试全绿。
- [ ] **5.2** spec 自查：grep 确认无 fav_count、route 薄调 service、零 schema 变更、业务逻辑不在 route。

## 校验命令汇总

```bash
cd backend
python -m pytest -v                                  # 全量（5.1）
python -m pytest tests/test_favorites.py -v          # 仅 favorites（4.7 后）
python -c "from app.main import app; print([r.path for r in app.routes if 'favorite' in r.path])"
```

## 回滚点

- **步骤 1-2 后**：删 schemas/favorite.py + services/favorites.py，DB 无影响。
- **步骤 3 后**：删 api/favorites.py + posts.py 的 favorite 端点 + __init__ 挂载，端点消失。
- **全切片回滚**：`git revert`，零 schema 变更，无迁移需反向。

## 风险点（来自 design §9）

- position 空洞（调序/移项后不连续）：单用户量级可接受，前端按 position 排序。
- 默认夹 name 冲突：用 name 约定（无 is_default 字段，不改 schema）。
