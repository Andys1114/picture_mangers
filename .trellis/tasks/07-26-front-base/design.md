# 前台基座与切换 · 技术设计

## 1. 目录切换与迁移策略

三个独立提交，保证每步可回滚：

1. **纯改名**：`git mv frontend frontend-legacy`，不改任何内容 → git 按 rename 追踪，`--follow` 可追历史。
2. **废弃标注**：`frontend-legacy/README.md` 顶部插入废弃横幅（已废弃 / 存档原因 / 新前端位置 / 如何手动运行）。
3. **新脚手架**：新建 `frontend/`，首个可启动版本。

回滚点：任一提交单独 revert 即可；`dev.py` 全程不改（写死 `ROOT/"frontend"`，preflight 只查 `frontend/node_modules`）。

## 2. 新前端骨架

### 2.1 从旧代码移植（改造后复用，不是照抄）

| 来源（frontend-legacy） | 处理 |
|---|---|
| `next.config.ts`（/api、/media rewrite） | 原样移植 |
| `middleware.ts`（cookie 门卫，PUBLIC=/login,/setup） | 原样移植 |
| `lib/api.ts` / `lib/types.ts` | 移植 + `listPosts` 加 `ratings` 参数 |
| `lib/queryClient.ts`、`lib/utils.ts`、`lib/colors.ts` | 移植；colors.ts 改为从新令牌导出分类/评级色 |
| `hooks/useAuth useMe useInfinitePosts useUpdateSafeMode` | 移植；`useInfinitePosts` 加 ratings 入参 |
| `components/ui/*`（无 Radix 自研） | 按新令牌重写样式，保留 API 形状 |
| `package.json` 依赖集 | 同集合起步 + `@fontsource` 字体包；不加新框架 |

### 2.2 目录结构（目标）

```
frontend/
├── app/
│   ├── layout.tsx            # 字体 + Providers + 全局 Toaster
│   ├── providers.tsx
│   ├── login/page.tsx
│   ├── setup/page.tsx
│   └── (protected)/
│       ├── layout.tsx        # 认证壳（无导航侧栏，前台就是全屏浏览）
│       └── page.tsx          # 浏览页 = 顶栏 + 筛选栏 + 瀑布流 + 灯箱挂载
├── components/
│   ├── browse/
│   │   ├── topbar.tsx  user-menu.tsx  safe-mode-button.tsx  search-box.tsx
│   │   ├── filter-rail/ (rail.tsx  rail-tags.tsx  rail-ratings.tsx  rail-chips.tsx  use-auto-collapse.ts)
│   │   ├── masonry-grid.tsx  post-card.tsx
│   │   └── states.tsx        # 骨架/空库/无结果/失败
│   ├── lightbox/ (lightbox.tsx  info-panel.tsx  use-lightbox-url.ts  use-swipe.ts)
│   ├── common/auth-card.tsx
│   └── ui/ (button badge input password-input skeleton sonner dropdown-menu sheet)
├── styles/globals.css        # 全部 CSS 变量令牌 + 玻璃层/骨架动画工具类
├── tailwind.config.ts        # 令牌映射（色/圆角/字体/缓动）
└── middleware.ts
```

## 3. 设计令牌落法

- `globals.css` `:root` 定义设计稿 Design Tokens 全表变量（`--bg-page: #07070b`、玻璃层 rgba、文字四级、强调渐变两端色、五分类色、三评级色、圆角、`--ease: cubic-bezier(0.22,1,0.36,1)`）。暗色单主题，不做浅色。
- `tailwind.config.ts` 把变量映射成语义类（`bg-glass`、`text-secondary`、`rounded-card`…）；渐变、光晕用工具类组合。
- 玻璃层做成两个工具类（`.glass-bar` 0.72/blur20、`.glass-pop` 0.92/blur22）避免每处手写 rgba。
- 字体：`@fontsource/noto-sans-sc`（400/500/700）、`@fontsource/space-grotesk`（500/700）、`@fontsource/jetbrains-mono`（400/600），在 `app/layout.tsx` 导入 css，npm 自托管、带 unicode-range 分片，无构建期外网依赖。CSS 变量 `--font-ui/--font-brand/--font-mono` 供 tailwind fontFamily 引用。
- `prefers-reduced-motion`：globals.css 全局 `@media` 关动画（沿用旧前端做法）。

## 4. 状态与数据流

| 状态 | 归属 |
|---|---|
| 已选标签/评级筛选 | URL：`?tags=a+b`、`?ratings=safe,questionable`（刷新/分享可还原） |
| 灯箱开合与当前图 | URL：`?photoId=` |
| 筛选栏折叠/图钉 | 本地：localStorage `rail_pinned` + 8s 无操作定时器（hover/focus 重置） |
| 服务端数据 | TanStack Query：`useMe`、`useInfinitePosts({tags, ratings})`、`usePost(id)`、`usePostNav(id)`（/next） |
| 安全模式 | 服务端权威；PATCH 后 invalidate `me` + posts 列表 |

灯箱 URL 语义（与 CONTEXT.md"详情页"一致）：点图 push `?photoId=`；←→ replace；Esc/遮罩/返回 = history.back；直达（无列表上下文）禁翻页、走 `usePost` 单图。移动端手势：`use-swipe.ts` 用 Pointer Events 实现左右滑翻页（复用 /next）、下滑关闭、信息半层上拉。

## 5. 后端改动（唯一一处）

`GET /api/posts` 增加 `ratings` 查询参数（逗号分隔枚举，Pydantic 校验非法值 422）：

```python
# api/posts.py
ratings: str = Query("", description="Comma-separated rating filter, ignored when safe mode is on")
# services/search.py list_posts(...)
if safe_mode:
    stmt = stmt.where(Post.rating == "safe")      # 现状不变，参数被忽略
elif ratings:
    stmt = stmt.where(Post.rating.in_(ratings))    # 解析后的合法子集
```

`/posts/{id}/next` 本任务不加 ratings（沿用全局翻页语义，偏差已在 prd 记录）。

## 6. 兼容性与风险

- **旧前端可运行性**：legacy 目录自带 node_modules 与 lockfile，改名不破坏；其 `npm run dev` 仍走 3000 端口（与新前端二选一手动跑）。
- **接口兼容**：`ratings` 是新增可选参数，legacy 不传 → 行为与今天完全一致；后端无破坏性改动。
- **`.next/`、`node_modules/` 改名开销**：二者在 .gitignore 内，git mv 实际只移动源码文件。
- **风险：瀑布流/灯箱是交互密集区** → implement.md 把它们排在有真实数据（seed）之后做，边做边浏览器验证。
- **风险：CJK 字体体积** → fontsource 按 unicode-range 分片，浏览器只拉用到的分片；不自打包全量 woff2。
