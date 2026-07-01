# Journal - Andys1114 (Part 1)

> AI development session journal
> Started: 2026-06-28

---

## 2026-06-29 — 子任务 06-29-backend-skeleton 完成

**任务**: 后端骨架 + 数据模型 + 单用户认证(父任务 06-28-gallery-app 的子任务 1)

**完成内容**:
- FastAPI + SQLAlchemy 2.0 + SQLite(WAL) + Alembic 脚手架
- 8 张 ORM 表(posts/tags/post_tags/tag_implications/favorites/favorite_items/users/sessions)
- 单用户认证:首次 /setup 向导 + /login + /logout + /me,cookie 会话保护
- 统一错误信封 + CORS + 健康检查
- pytest 11 用例覆盖 AC1-AC12 全绿
- 填充 5 个后端 spec 文件(directory-structure/database-guidelines/error-handling/quality-guidelines/logging-guidelines)

**关键决策**:
- session 存 DB 而非 JWT —— 个人单用户场景,DB session 可即时失效(logout 删记录),实现简单
- Alembic 而非 create_all —— 为后续 7 个子任务的 schema 演进铺路
- 严格只做地基 + auth + health,不碰业务路由 —— 避免范围蔓延

**踩坑**:
- ZCode Bash 工具初期崩溃(0xC0000142,Cygwin fork),重装 Git for Windows + rebase 后恢复
- 长文本内联手写 design.md 时出现模型输出退化(乱码/重复),改用分段 Edit 写入规避
- alembic.ini 用 locale 编码(GBK)读取,不能含非 ASCII 注释
- 测试里 `from app.db import SessionLocal` 拿的是 patch 前引用,改用 `db_module.SessionLocal` 访问被 patch 的属性

**提交**: 2555ac0 / 05b90fb / 451c761 / 997b226
**状态**: 已归档至 archive/2026-06/

**下一步**: 父任务剩余 7 个子任务。建议下一个做子任务 2(标签搜索编译器)或子任务 3(媒体处理管道),两者都只依赖子任务 1,可并行。

---

## 2026-06-30 — grilling 会话 + 领域模型决策落地(子任务 06-30-domain-spec-landing)

**任务**: 用 `/grill-with-docs`(grilling + domain-modeling skill)对现有规范做压力测试,敲定领域模型并落地。

**完成内容**:
- grilling 一对一访谈,敲定 10 条领域决策:单用户语义(bootstrap-single-user)、标签连带/废弃(只有 implication 无 alias、is_deprecated 独立)、连带防环(写入前反向可达性+闭包带已访问集合)、post_count 语义、收藏(纯收藏夹+默认夹、不统计收藏次数)、重复图(md5+phash 异步、duplicate_of_id、主视图默认隐藏)、评级三档、连带时机(写入时算实)、搜索(本期仅 AND)、抓取去重(source_id 阶段+md5 兜底+部分唯一索引)。
- 建根目录 `CONTEXT.md`(中文术语表,5 组 14 词)。
- 建 `docs/adr/0001-implication-materialized-at-write-time.md`(连带写入时算实,最难反悔的决策)。
- 改 `.trellis/spec/backend/database-guidelines.md`:删 fav_count、post_count 改为 post_tags 行数、递归 CTE 改为仅写入时、新增重复图与抓取去重小节。
- 改 `.trellis/spec/backend/quality-guidelines.md`:加搜索/评级/重复图语义、禁用 fav_count、禁用读时递归搜索、补检查项。
- 回改父任务 `06-28-gallery-app` 的 prd.md 与 design.md 消解三处冲突:搜索语法本期仅 AND(NOT/OR/通配留后续)、fav_count 删除、连带机制改写入时算实。顺带对齐 F5/AC4 重复图、design.md 第 3 节查询编译流程与关键设计决策。

**关键决策**:
- 连带写入时算实而非读时递归——让 post_tags 永远是展开集,搜索变简单、post_count 永远准、删连带是"黏"的。这是 ADR-0001 的核心。
- 搜索本期砍到只做 AND——回退了原 PRD 的 NOT/OR/通配,用户确认留后续版本。
- 不统计收藏次数、删 Post.fav_count——回退了原 PRD 的冗余字段。

**待办(留给后续实现子任务)**: 一条 Alembic 迁移要删 Post.fav_count、加 Post.duplicate_of_id(自引用 FK,SET NULL)、加 (source_site,source_id) 部分唯一索引。

**状态**: 文档落地完成,待提交。

---

## 2026-06-30 — 前端 grilling + 前端 spec 落地(子任务 06-30-frontend-spec-landing)

**任务**: 用 `/grill-with-docs` 对前端做压力测试(前端要交给 `/ui-ux-pro-max` 建),敲定决策并落地。

**完成内容**:
- grilling 敲定 7 条前端决策:技术栈(Next 15 App Router + TS + Tailwind + shadcn/ui + lucide)、渲染取数(客户端为主 + TanStack Query,RSC 只做外壳/中间件)、详情页(`?photoId=` 软导航浮层,无独立 /post/[id] 路由,直达禁用翻页)、图片管线(FastAPI StaticFiles /media + Next rewrite 同源 + Next/Image unoptimized + tier loader,blur-up 暂缓)、安全模式(挂 Session、新会话默认开自动回安全)、鉴权流(中间件挡 cookie + /login /setup 调 /api/auth/status 分流 + provider 调 /api/me)、交付顺序(切片1 设计基座+浏览页+lightbox → 标签/搜索 → 收藏 → 导入/抓取 → 登录/设置;先补后端最小接口不造 mock;桌面优先+窄屏不崩,移动端后议)。
- 填满 `.trellis/spec/frontend/` 6 个空模板(directory-structure/component-guidelines/hook-guidelines/state-management/quality-guidelines/type-safety),index 全标 Filled。
- CONTEXT.md 补"前端界面"组(浏览页/详情页 Lightbox/安全模式)。
- 回改父 PRD:F1 安全模式挂 session、F2 详情页改 ?photoId 软导航、F8 鉴权流细化、第 5 节约束补前端栈。

**关键决策**:
- 详情页用 `?photoId` query param 软导航而非拦截路由——更简单、贴合 lightbox;翻页用 replace 避免后退地狱,直达场景关闭用 replace 抹参数(不能 back)。
- 安全模式挂 Session 不挂 User——实现"新会话自动回安全"的防误看语义。
- 前端不造 mock,等后端最小接口(posts 列表/单图/auth-status/me/media)就位再开切片1。

**待办(后端)**: 新接口 GET /api/posts、GET /api/posts/{id}、GET /api/auth/status、PATCH /api/me/settings、GET /api/me(含 safe_mode)、StaticFiles /media;迁移加 Session.safe_mode(默认 true),连同上一轮的 fav_count 删除/duplicate_of_id/来源唯一索引进同一条迁移。

**状态**: 文档落地完成,待提交。




## Session 1: 前端骨架+浏览页 与 最小后端端点

**Date**: 2026-07-01
**Task**: 前端骨架+浏览页 与 最小后端端点
**Branch**: `main`

### Summary

用 Trellis 工作流交付 06-30-frontend-skeleton-browse（父 design #5）。先补 spec 合规的最小后端端点（Session.safe_mode + migration、/api/auth/me + settings PATCH、/api/posts 列表/详情、/media StaticFiles、search AND 服务、NotFoundError、post schemas、test_posts 11 例，pytest 25/25 绿、dev seed 脚本），再前端真接零 mock（Next 15 + TS strict + Tailwind + shadcn 风格 UI + TanStack Query：鉴权流 middleware+providers+setup/login/settings、浏览页毛玻璃顶栏+搜索框+安全模式开关+CSS columns 瀑布流+无限滚动+卡片 hover；lint/tsc/build 干净、端到端联调通过）。期间 before-dev 拦截到方案违反 spec（禁前端 mock + safe_mode 服务端权威），改走先补后端端点路径并更新 spec。修复一处 dev server .next 缓存脏导致 main-app.js 404 卡在加载中的问题。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `085a07f` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: 前端视觉美化打磨

**Date**: 2026-07-01
**Task**: 前端视觉美化打磨
**Branch**: `main`

### Summary

用 Trellis 工作流交付 07-01-frontend-visual-polish：在已交付骨架上做纯 Tailwind/CSS 视觉打磨，零新依赖、不改功能契约（trellis-check 确认 api/types/hooks/middleware/providers 零修改）。改动：next/font 真正加载 Inter+JetBrains Mono（此前仅声明未加载）、补 elevation/shimmer/focus token；新建 AuthCard（径向渐变+品牌 wordmark）与 PasswordInput（show/hide）复用至 login/setup；settings 分三段卡片；顶栏 logo 加图标+滚动渐隐加 opacity；卡片 hover 微缩放+图片淡入+底部渐变遮罩+分级 chip（图标+标签+色，color-not-only）+★ 触屏始终可见；瀑布流 stagger 入场+shimmer skeleton+空态图标+错误重试；Button press 缩放+统一 ease-out。tsc/lint/build 全干净、e2e 冒烟通过、trellis-check PASS。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `df9e5fb` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
