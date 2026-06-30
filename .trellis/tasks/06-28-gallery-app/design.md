# 类 Danbooru 现代画廊图库应用 — 技术设计

> 需求见 `prd.md`。本文件描述技术架构、数据模型、子系统边界、数据流、拆分策略。

## 1. 整体架构

前后端分离（方案 A），两个独立进程。

- **frontend/** — Next.js 15 App Router + TypeScript。瀑布流 / lightbox / 标签树用客户端组件；首屏可用 RSC 预渲染。状态：TanStack Query（服务端数据）+ Zustand（UI 状态：视图/安全模式）。
- **backend/** — FastAPI（Python 3.11+）。三层：API 路由层、Services 业务逻辑层、数据层（SQLAlchemy 2.0 + SQLite WAL + FTS5）。
- **后台任务** — APScheduler + 线程池，承载 Danbooru 抓取、批量导入、缩略图生成（长任务，不阻塞 API 响应）。

### 选型理由
- **Next.js 15 + TS** — 瀑布流/lightbox 是重交互，客户端组件 + React 生态（shadcn/ui、framer-motion）最顺手。
- **FastAPI** — 异步，OpenAPI 文档自动，Pydantic 类型贯通前后端契约。
- **SQLAlchemy 2.0 + SQLite (WAL)** — WAL 让 SQLite 支持并发读写，个人图库量级足够；无需 Postgres。
- **SQLite FTS5** — 内置全文搜索，标签补全/搜索极快。
- **Pillow + imagehash** — 缩略图生成 + 感知哈希（pHash）去重。
- **APScheduler** — 轻量任务调度，无需 Celery/Redis（单机单用户用不上）。

### 数据进入流
- 本地导入：文件夹扫描 → md5/phash 去重 → 存原图 → Pillow 生成 thumb/preview → 写 DB（无标签，后续手动打）。
- Danbooru 抓取：API 查询 → 下载图 + 标签 + source + rating → 复用媒体管道 → 写 DB（含 implication）。

---

## 2. 数据模型

核心实体关系：

- `posts` 1—N `post_tags` N—1 `tags`（图片-标签多对多）
- `tags` 通过 `tag_implications` 形成有向图（implication 语义）
- `posts` 1—N `favorite_items` N—1 `favorites`（图片-收藏夹多对多）
- `users` 单条记录（首次启动初始化）；会话用 cookie

### posts（图片主表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| source_site | TEXT | 'danbooru' / 'local' / NULL |
| source_id | TEXT | 原站 post id（抓取来源；本地导入为 NULL） |
| source_url | TEXT | 原始页面 URL |
| file_path | TEXT | 原图相对路径（media/posts/{id}.{ext}） |
| thumb_path | TEXT | 缩略图路径（150×150，详情页/列表小图） |
| preview_path | TEXT | 中等预览图路径（850×850，瀑布流用） |
| file_ext | TEXT | png/jpg/webp/gif/apng |
| is_animated | BOOLEAN | 动图标记（影响播放器） |
| width, height | INTEGER | 原图尺寸 |
| file_size | INTEGER | 字节 |
| md5 | TEXT UNIQUE | 精确去重 |
| phash | TEXT | 感知哈希（相似图去重） |
| is_duplicate | BOOLEAN | 重复图快筛标记（权威来源为 duplicate_of_id） |
| duplicate_of_id | INTEGER FK → posts.id | 指向原图；NULL 表示非重复。ondelete=SET NULL。待迁移添加 |
| rating | TEXT | 'safe' / 'questionable' / 'explicit' |
| created_at, updated_at | TIMESTAMP | |

> 注：本期**不设 `fav_count`**（不统计收藏次数）。是否收藏过由 `favorite_items` 成员关系判断。

### tags（标签表）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE | 标签名 |
| category | TEXT | 'general' / 'character' / 'copyright' / 'artist' / 'meta' |
| post_count | INTEGER | 使用次数（冗余，加速标签云排序） |
| is_deprecated | BOOLEAN | 废弃标记（抓取可能带回） |
| created_at | TIMESTAMP | |

### post_tags（图片-标签关联）
| 字段 | 类型 | 说明 |
|---|---|---|
| post_id | INTEGER FK → posts.id | |
| tag_id | INTEGER FK → tags.id | |
| | PRIMARY KEY (post_id, tag_id) | |
| | 索引：tag_id（反向查询"含某标签的所有图"） | |

### tag_implications（标签含义，搜索语义）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| antecedent_id | INTEGER FK → tags.id | 子标签（如 miku） |
| consequent_id | INTEGER FK → tags.id | 父标签（如 vocaloid） |
| status | TEXT | 'active'（默认，抓取数据带来） |
| | UNIQUE (antecedent_id, consequent_id) | |

语义：打 antecedent 自动等于打 consequent。**写入时算实**——打标签（含抓取/导入）当场把前因的整条连带链算出闭包、写进 `post_tags`；连带后加时回填老图。搜索直接查 `post_tags`（AND），不做读时递归。详见 `docs/adr/0001-implication-materialized-at-write-time.md`。

### favorites / favorite_items（收藏夹/图集）
| 字段 | 类型 | 说明 |
|---|---|---|
| favorites.id | INTEGER PK | |
| favorites.name | TEXT | 图集名 |
| favorites.created_at | TIMESTAMP | |
| favorite_items.favorite_id | INTEGER FK → favorites.id | |
| favorite_items.post_id | INTEGER FK → posts.id | |
| favorite_items.position | INTEGER | 图集内排序 |
| | PRIMARY KEY (favorite_id, post_id) | |

### users / sessions（单用户登录）
| 字段 | 类型 | 说明 |
|---|---|---|
| users.id | INTEGER PK | |
| users.username | TEXT UNIQUE | |
| users.password_hash | TEXT | bcrypt |
| sessions.id | TEXT PK | 随机 token |
| sessions.user_id | INTEGER FK → users.id | |
| sessions.expires_at | TIMESTAMP | |

### 关键设计决策
- **冗余字段 `post_count`**：标签云按使用次数排序时避免 JOIN+COUNT。因连带写入时算实，`post_tags` 永远是展开集，故 `post_count` = 该标签在 `post_tags` 的行数，永远准，无需懒重算。**不设 `fav_count`**（不按收藏数排序）。
- **implication 写入时算实（非读时递归）**：搜索 `miku` 命中 `vocaloid` 是因为打 `miku` 时已把 `vocaloid` 写进 `post_tags`。递归 CTE 仅用于写入时算闭包 + 防环（新建连带前反向可达性检查，成环则 409）。见 ADR-0001。
- **pHash + md5 双重去重**：md5 抓完全相同文件（直接跳过、不建记录）；pHash（Hamming 距离 < 阈值，默认 8）在导入后异步计算，命中近似则标记 `is_duplicate` 并填 `duplicate_of_id` 指向原图。重复图仍入库但**主视图默认隐藏**，可在专门视图查看、仍可被收藏。
- **抓取去重**：`(source_site, source_id)` 对非空来源部分唯一索引；抓取列表阶段按此跳过已抓项，下载后 md5 兜底走重复图流程。单来源字段，跨站重复不另建主图。
- **三档图存储**：thumb（列表小图）、preview（瀑布流中等图）、原图。瀑布流用 preview 避免加载原图。

---

## 3. 标签搜索语法与查询编译

### 支持的语法（本期）
- `tag1 tag2` — 交集（AND）
- `rating:safe|questionable|explicit` — 分级过滤

> **后续版本**再考虑 `-tag1`(NOT)、`~tag1 ~tag2`(OR)、`tag1*`(通配)。本期不做，不写假设其存在的测试。

排序：`order:id`（默认，入库时间倒序）/ `order:random`。分页：每页 40 张，无限滚动。**不设 `order:favcount`**（不统计收藏次数）。

### 查询编译流程（后端 search service）
1. **Parser** — 把搜索串解析成 token 列表：正向标签（AND）与 `rating:` token。本期不产生 NOT/OR/WILD token。
2. **无需读时连带展开** — 因连带在写入时已算实（ADR-0001），`post_tags` 已含展开后的完整标签集。搜索 `miku` 直接匹配 `post_tags` 即可命中 `vocaloid` 的图，**不跑递归 CTE**。
3. **Compiler** — 用 SQLAlchemy Core 构建参数化查询：
   - AND：对每个正向标签，`post_id IN (SELECT post_id FROM post_tags WHERE tag_id = ?)`，多标签用 `INTERSECT` 组合。
   - rating：附加 `posts.rating = ?`（安全模式开启时后端注入 `safe`）。
   - 默认排除 `duplicate_of_id IS NOT NULL` 的重复图（专门视图才返回）。

### 安全模式（后端全局注入）
安全模式开关不在前端搜索框写死，而是**后端全局拦截**：每个查询编译前，若安全模式开启，自动把 `rating:safe` 注入 token 流。前端切换开关即时生效，搜索框保持纯净。**默认开启。**

### 前端搜索框交互
标签输入后 chip 化：普通标签按类型着色。输入时下拉自动补全（查 tags 表 `name LIKE '...%'` 按 post_count 排序）。

---

## 4. 导入与抓取子系统

两条数据进入路径，共用一套去重 + 媒体处理管道。

### 共享媒体处理管道（services/media.py）
1. 读取/下载文件字节
2. md5 计算 → 查 DB → 命中则跳过（精确去重）
3. phash 计算 → 查相似图（Hamming 距离 < 阈值）→ 标记 `is_duplicate`（仍入库）
4. Pillow 生成缩略图：thumb（150×150）、preview（850×850）；动图取首帧做缩略图，原图保留动画
5. 存原图 + 缩略图到 `media/posts/{id}/`
6. 写 posts + post_tags（抓取带回的 implication 一并入库）

### 本地导入（路径 A）
- 后台任务递归扫描指定文件夹，支持格式：png/jpg/webp/gif/apng。
- **增量扫描**：记录已扫描路径 + 文件 mtime，二次扫描只处理新文件。
- 本地图导入时**无标签**，之后由用户手动打标签（短期不接 ML 自动打标签）。
- 进度反馈：前端轮询任务状态端点，显示"已处理 X/Y，重复 N"。

### Danbooru 抓取（路径 B，scraper 抽象）
- 抓取器抽象基类 `scrapers/base.py`：
  - `search(query, page) → list[ScrapedPost]`（按标签搜索）
  - `fetch(post_id) → ScrapedPost`（按 id 取单张）
  - `ScrapedPost` dataclass：source_id、image_url、tags[{name, category}]、rating、source_url、implications[]
- `scrapers/danbooru.py`（首个实现）：baseurl `https://danbooru.donmai.us`，公共 API（匿名，限速 1 req/s）。
- 预留 `gelbooru.py` / `moebooru.py`，同接口。
- **限速与重试**：适配器内令牌桶限速 1 req/s；失败指数退避重试。
- **implication 随抓取带回**：从 Danbooru tags 端点批量拉取 implication 关系，建库时拉一次，之后增量。

### 重复处理策略
- md5 完全相同 → 直接跳过，不建记录。
- phash Hamming 距离 < 阈值（默认 8）→ 导入后异步计算，命中则标记 `is_duplicate` 并填 `duplicate_of_id` 指向原图。重复图仍入库，但**主视图默认隐藏**，在专门视图查看、仍可被收藏。

### 后台任务调度（APScheduler）
抓取/导入是长任务，走后台线程池不阻塞 API。任务状态存内存（单机够用），前端轮询 `/api/tasks/{id}` 看进度。

---

## 5. UI 详细设计

### 页面地图
- `/` — 浏览页（瀑布流主页）
- `/post/[id]` — 详情页（lightbox + 左侧精简浮层）
- `/tags` — 标签页（标签树/云 + 搜索）
- `/favorites/[id]` — 图集详情页
- `/upload` — 上传/导入页（本地导入 + Danbooru 抓取）
- `/login` — 登录页（未登录拦截）
- `/setup` — 首次启动向导（设置用户名+密码）

### 页面 1：浏览页 `/`（沉浸瀑布流）
- 顶栏：半透明毛玻璃，滚动渐隐，hover/置顶复现。含 Logo、搜索框、安全模式开关（盾牌图标）、登录、导入入口、设置。
- 无边框瀑布流：CSS columns 实现，等宽列、按高度排布，极小 gap（4px）。
- 卡片 hover 浮现控件：收藏 ★、分级色块（右下角）、疑似重复标记（左上角）。
- 左侧可滑出抽屉：标签筛选（按类型折叠 + 热门标签云，点击即加入搜索）。
- 无限滚动：IntersectionObserver 触发加载下一页。

### 页面 2：详情页 `/post/[id]`（lightbox 沉浸）
- 黑底全屏，图片主体在右侧/居中。
- 左侧半透明浮层信息面板：默认精简（ID/尺寸/标签按类型分组首行），"展开全部"显示所有标签 + source_url + phash + md5 + 创建时间。
- implication 折叠树：父标签可展开看 implied 子标签。
- 标签着色：character 蓝 / copyright 紫 / artist 黄 / general 灰 / meta 青。点击标签跳转搜索。
- 键盘导航：← → 翻页，F 收藏，E 编辑，Esc 返回。
- 动图自动循环播放，点击暂停/播放。
- 编辑模式：增删标签、改分级、加入图集。

### 页面 3：标签页 `/tags`
- 按类型（category）分组：角色/作品/作者/通用，各自可折叠。
- 每个标签显示 post_count，按计数排序。
- implication 父节点可展开看 implied 子标签。
- 点击标签 → 跳转浏览页搜索该标签。

### 页面 4：上传/导入页 `/upload`
- 两个 tab：本地文件夹导入 / Danbooru 抓取。
- 本地：输入路径 → 开始扫描 → 进度条（处理数/总数/重复数）。
- 抓取：输入查询 + 数量 → 开始抓取 → 进度条（已抓/总数/重复/新增 implication）。
- 任务历史列表（可取消）。

### 视觉规范（深色沉浸）
- 配色：背景 #0a0a0b（近黑）/ 表面 #141416（卡片浮层）/ 边框 #1f1f23（极淡）/ 文字 #e5e5e7 / 次文字 #8a8a90 / 强调 #3b82f6（蓝）。分级色：safe #22c55e / q #eab308 / e #ef4444。
- 字体：界面 Inter + CJK 系统字体栈；等宽（标签/md5）JetBrains Mono。
- 间距：瀑布流 gap 4px；卡片 padding 16px；浮层圆角 12px。
- 动效：framer-motion，翻页/抽屉/浮层过渡 200-300ms ease-out；hover 控件淡入 150ms。
- 标签配色先用经典色系，后续再定。

---

## 6. API 设计 + 单用户认证

### API 端点（全部 `/api` 前缀，除 login 外需认证）

**认证**
- `POST /api/auth/login` `{username, password} → {token}`
- `POST /api/auth/logout`
- `GET /api/auth/me` → 当前用户

**posts（浏览/搜索/详情）**
- `GET /api/posts?tags=&page=&limit=&order=&safe=` → 分页列表（tags 编译成搜索语法；列表返回精简字段，不含完整标签）
- `GET /api/posts/{id}` → 单图详情（含展开的标签）
- `GET /api/posts/{id}/next` → 翻页上下文（上一张/下一张 id）
- `PATCH /api/posts/{id}` → 编辑（改标签/分级）
- `DELETE /api/posts/{id}` → 删除
- `GET /api/media/posts/{id}/{size}` → 原图/preview/thumb 静态文件（size: original|preview|thumb）

**tags**
- `GET /api/tags?search=&category=&order=count` → 标签列表（补全 + 标签页用）
- `GET /api/tags/tree` → implication 树结构（标签页折叠展示）
- `GET /api/tags/{id}` → 单标签详情
- `POST /api/tags` → 新建标签
- `PATCH /api/tags/{id}` → 改标签（类别/重命名）

**favorites（图集）**
- `GET /api/favorites` → 图集列表
- `POST /api/favorites` → 新建图集
- `GET /api/favorites/{id}` → 图集详情（含 posts）
- `POST /api/favorites/{id}/items {post_id}` → 加入图集
- `DELETE /api/favorites/{id}/items/{post_id}` → 移出图集
- `PATCH /api/favorites/{id}/items/{post_id}` → 调整排序

**import（导入/抓取）**
- `POST /api/import/scan {path}` → 启动本地扫描任务 → `{task_id}`
- `POST /api/import/scrape {query, source:'danbooru', limit}` → 启动抓取任务 → `{task_id}`
- `GET /api/tasks/{id}` → 任务进度轮询（processed/total/duplicates）

**settings**
- `GET /api/settings` → `{safe_mode, page_size, ...}`
- `PATCH /api/settings` → 更新（safe_mode 同步存后端）

### 响应约定
- 统一信封：成功 `{"data": ..., "meta": {"page":1, "total":1234}}`，错误 `{"error": {"code", "message"}}`。
- posts 列表返回精简字段（不含完整标签），详情接口才返回展开标签，减少列表 payload。
- 分页用 page + limit（初期 offset 够用，cursor 分页后期再优化）。

### 单用户认证流程
- **首次启动**：后端检测 DB 无 user 记录 → 前端访问任意页 → 重定向 `/setup` → 设置用户名+密码 → bcrypt 哈希存库（仅此一条 user 记录）→ 自动登录，之后 `/setup` 不可访问。
- **登录**：`POST /auth/login` → 校验 bcrypt → 签发 session token → 存 HttpOnly cookie（防 XSS）。
- **保护**：所有 `/api/*`（除 `/auth/login`）强制校验 cookie。未登录 → 401 → 前端跳 `/login`。
- 个人图库不存在公开浏览；想公开可后续加 guest 模式。

---

## 7. 项目目录结构

```
picture_mangers/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI 入口，挂载路由 + 中间件
│   │   ├── config.py            配置（DB 路径、media 目录、限速等）
│   │   ├── db.py                SQLAlchemy engine + session
│   │   ├── models/              ORM 模型（post, tag, implication, favorite, user）
│   │   ├── schemas/             Pydantic 请求/响应模型
│   │   ├── api/                 路由（auth, posts, tags, favorites, import, settings）
│   │   ├── services/            业务逻辑（search 查询编译器、media 媒体管道、rating 安全过滤、auth）
│   │   ├── scrapers/            抓取适配器（base 抽象 + danbooru 实现）
│   │   └── tasks/               后台任务（scheduler APScheduler 管理）
│   ├── media/                   图片存储（gitignore）
│   │   └── posts/{id}/{original,preview,thumb}
│   ├── tests/
│   ├── picture_mangers.db       SQLite（gitignore）
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── app/                     Next.js App Router
│   │   ├── (auth)/login/
│   │   ├── (app)/               带顶栏布局：page(浏览), post/[id], tags, favorites/[id], upload
│   │   ├── setup/
│   │   └── layout.tsx
│   ├── components/              masonry/ search/ post/ tags/ ui(shadcn)
│   ├── lib/                     api(client typed)/ stores(Zustand)/ hooks(TanStack Query)
│   ├── package.json
│   └── tsconfig.json
├── .trellis/                    （已存在，Trellis 管理）
└── README.md
```

---

## 8. 拆分策略（父任务 → 子任务）

本任务为父任务，含多个可独立验证的交付物。建议拆成以下子任务，每个独立 prd/design/implement + 独立验证。依赖关系写在各子任务的 prd/implement 里，不靠树位置隐含。

1. **后端骨架 + 数据模型 + 单用户认证** — 项目脚手架、ORM 模型、migration、auth 流程（/setup + login + cookie 保护）。无依赖。
2. **标签搜索编译器** — Parser + Compiler（SQLAlchemy Core），AND + rating 过滤；连带已在写入时算实，搜索不递归。依赖 1（需要 tags/implications 模型）。
3. **媒体处理管道** — md5/phash 去重 + Pillow 缩略图生成。依赖 1。
4. **Danbooru 抓取器** — scraper 抽象 + danbooru 适配器 + implication 批量拉取。依赖 1、3（复用媒体管道）。
5. **前端骨架 + 浏览页瀑布流** — Next.js 脚手架、顶栏、搜索框、MasonryGrid、无限滚动、安全模式开关。依赖 1、2（需要 posts API + 搜索）。
6. **详情页 lightbox** — lightbox 布局、左侧浮层、implication 树、标签着色、键盘导航、动图播放。依赖 5。
7. **标签页 + 搜索框** — /tags 标签树、搜索框 chip 化 + 自动补全。依赖 2（需要 tags API + implication 树）、5（前端骨架）。注：搜索框基础结构在子任务 5 已搭建，本子任务做 chip 化着色 + 自动补全交互。
8. **导入页 + 收藏夹** — /upload 本地导入 + 抓取 UI、收藏夹管理、任务进度轮询。依赖 4、5。

子任务建议执行顺序：1 → (2,3 并行) → 4 → 5 → (6,7,8 按优先级)。







