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
