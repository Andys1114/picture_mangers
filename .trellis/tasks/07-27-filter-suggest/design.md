# 筛选与联想增强 · 技术设计

## 1. 后端 suggest 端点

- `backend/app/api/tags.py` 加路由（放在 `/tree` 之后、`/{tag_id}` 之前——FastAPI 按注册序匹配，`/suggest` 必须先于路径参数路由注册，否则被 `/{tag_id}` 吞掉返回 422）：

```python
@router.get("/suggest", response_model=TagSuggestResponse)
def suggest(prefix: str = Query(""), limit: int = Query(10, ge=1, le=20), ...)
```

- 服务层 `services/tags.py` 加 `suggest_tags(db, prefix, limit)`：
  - `prefix.strip()` 为空 → `[]`。
  - `Tag.name.ilike(f"{escaped}%")`（转义 `%`/`_`）；排序 `is_deprecated asc, post_count desc, name asc`，limit。
  - `implies`：对命中集一次性查 `tag_implications`（antecedent_id in 命中 id）join Tag 取后果名，Python 端分组回填——不做 N+1。
- `schemas/tag.py` 加 `TagSuggestItem(name, category, post_count, is_deprecated, implies: list[str])` + `TagSuggestResponse(data: list[...])`。
- 错误矩阵：limit>20 → 422（Query 校验）；prefix 任意字符串合法（含中文/符号，ilike 转义兜底）。

## 2. 前端

### 数据层
- `lib/types.ts` 镜像 `TagSuggestItem/TagSuggestResponse`；`lib/api.ts` 加 `api.suggestTags(prefix, limit?)`；`lib/queryClient.ts` key `tags.suggest(prefix)`。
- `hooks/useTagSuggest.ts`：内部 `useDeferredValue`/自建 150ms 防抖态 + `enabled: prefix.trim().length >= 1`，staleTime 30s。
- 作者列表复用现有 `useTags`（`{category:"artist", order:"count"}` 参数化——hook 已支持参数即透传，若写死则扩参）。

### 组件
- `components/browse/filter-rail/rail-artists.tsx`：新区块（结构对齐 rail-tags，琥珀圆点 = artist 色令牌）；rail.tsx 与 filter-drawer.tsx 各插一行引用（内容组件单份）。
- `components/browse/search-suggest.tsx`：下拉本体（glass-pop、listbox 语义：`role="listbox"`/`option`、`aria-activedescendant`）；search-box.tsx 改造：受控当前词解析（光标所在空格分段）、键盘事件（↑↓ 改高亮、Enter 取高亮或提交、Esc 关）、blur/外点关闭；最近搜索存 `localStorage("recent_searches")`，提交时去重头插截断 5。
- `components/browse/artist-header.tsx`：`useTags` 缓存反查当前唯一 artist 标签，命中则替换标题行。

### 行为细节
- 防抖在 hook 内做（输入即时回显、请求延迟）；请求竞态由 TanStack Query key 隔离天然处理。
- 联想选中替换"当前词"：以光标位置切词，替换后光标落词尾 + 保持下拉关闭。
- 废弃项可选中但选中后输入框旁不出提示（设计稿只在下拉行内提示，不阻断）。

## 3. 兼容与风险

- 无破坏性接口改动；legacy 前端不受影响。
- `/suggest` 注册顺序是唯一结构性风险点（见上），pytest 用 `/api/tags/suggest?prefix=x` 直接回归。
- 键盘导航与 `/` 全局聚焦并存：下拉打开时 `/` 不再抢焦点（已在输入框内自然满足）。

## 4. 回滚

三个提交粒度：后端 suggest（⛳）、作者区+作者头部（⛳）、联想下拉（⛳）。任一 revert 不影响其余。
