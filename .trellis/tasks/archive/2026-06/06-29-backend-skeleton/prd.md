# 后端骨架 + 数据模型 + 单用户认证

> 父任务:`06-28-gallery-app`。本子任务建立后端项目脚手架、ORM 数据模型、单用户认证流程,为后续所有后端子任务提供地基。

---

## Goal

搭建 FastAPI 后端骨架,落地完整数据模型(posts / tags / post_tags / tag_implications / favorites / favorite_items / users / sessions),实现单用户认证(首次启动 /setup 向导 + 登录 + cookie 会话保护)。完成后,后端能启动、表结构已建、认证可用,但尚无业务路由(posts/tags/search 等留给后续子任务)。

## Scope(本期交付)

1. **后端项目脚手架** — `backend/` 目录结构、依赖管理、配置、可启动的 FastAPI 应用。
2. **数据库层** — SQLAlchemy 2.0 engine/session、SQLite WAL、Alembic migration 初始版本。
3. **完整 ORM 模型** — 第 2 节全部 8 张表。
4. **单用户认证** — /setup(首次)、/login、/logout、/me、cookie 会话、依赖注入保护。
5. **健康检查 + 基础中间件** — CORS、错误处理信封、健康检查端点。

## 非目标(留给后续子任务)

- posts/tags/favorites 业务路由、搜索编译器、媒体管道、抓取器。(分别在子任务 2-4、5-8)
- 前端(子任务 5+)。

## Requirements

### R1. 项目脚手架
- `backend/` 下:`app/{main.py, config.py, db.py, models/, schemas/, api/, services/}`。
- `requirements.txt` 与 `pyproject.toml` 双依赖管理(pyproject 为主)。
- `config.py` 读环境变量 + 默认值:DB 路径、media 目录、密钥、CORS origins。
- `main.py` 挂载路由 + 中间件 + 启动事件(初始化 DB / WAL pragma)。

### R2. 数据库层
- SQLite + WAL 模式(启动时 `PRAGMA journal_mode=WAL; synchronous=NORMAL;`)。
- SQLAlchemy 2.0 声明式 ORM。
- Alembic:初始 migration 建全部 8 张表 + 索引。
- 外键约束开启(`PRAGMA foreign_keys=ON`)。
- `db.py` 提供 `get_db` 依赖(会话生命周期)。

### R3. ORM 模型(8 张表)
按父任务 design.md 第 2 节定义:posts、tags、post_tags、tag_implications、favorites、favorite_items、users、sessions。
- 冗余字段保留(post_count、fav_count、is_duplicate)。
- post_tags 复合主键 (post_id, tag_id) + tag_id 索引。
- tag_implications UNIQUE (antecedent_id, consequent_id)。
- favorite_items 复合主键 + position 字段。

### R4. 单用户认证
- **首次启动**:`GET /api/auth/status` 返回 `{setup_required: bool}`。前端据此决定是否去 /setup。
- **/setup**:`POST /api/auth/setup {username, password}` — 仅在 DB 无 user 时可用,创建唯一 user(bcrypt),签发 session,返回 user 信息。已有 user 时返回 409。
- **/login**:`POST /api/auth/login {username, password}` — bcrypt 校验,签发 session token(随机),写 sessions 表,设 HttpOnly cookie。
- **/logout**:`POST /api/auth/logout` — 删除当前 session 记录,清 cookie。
- **/me**:`GET /api/auth/me` — 返回当前登录用户(需认证)。
- **保护依赖**:`get_current_user` 依赖,从 cookie 解析 token 查 sessions 表。所有受保护路由用此依赖;未登录返 401。
- **session 过期**:sessions.expires_at 过期的视为无效。

### R5. 健康检查 + 中间件
- `GET /api/health` → `{status: "ok"}`(无需认证)。
- CORS 中间件(可配置 origins)。
- 统一错误信封:`{"error": {"code", "message"}}`,HTTP 状态码正确。

## Constraints

- Python 3.11+。
- 所有 API 前缀 `/api`(/api/health、/api/auth/* 等)。
- 密码用 bcrypt(passlib 或 bcrypt 库)。
- session token 用 secrets.token_urlsafe(32)。
- 代码标识符与注释英文;面向用户的错误消息可中文。

## Acceptance Criteria

- [ ] AC1: `cd backend && uvicorn app.main:app --reload` 能成功启动,无报错。
- [ ] AC2: 访问 `GET /api/health` 返回 `{status:"ok"}`,HTTP 200。
- [ ] AC3: 访问 `GET /api/auth/status`(空 DB)返回 `{setup_required: true}`。
- [ ] AC4: `POST /api/auth/setup` 创建用户后,`GET /api/auth/status` 返回 `{setup_required: false}`。
- [ ] AC5: setup 后再次 `POST /api/auth/setup` 返回 409。
- [ ] AC6: `POST /api/auth/login` 正确密码返回 200 + 设 cookie;错误密码返回 401。
- [ ] AC7: 带 cookie `GET /api/auth/me` 返回当前用户;不带 cookie 返回 401。
- [ ] AC8: `POST /api/auth/logout` 后,旧 cookie 访问 `/api/auth/me` 返回 401。
- [ ] AC9: SQLite 文件生成,`PRAGMA journal_mode` 为 WAL,`PRAGMA foreign_keys` 为 ON。
- [ ] AC10: Alembic migration 可重放(干净 DB 上 `alembic upgrade head` 建全部 8 表)。
- [ ] AC11: 8 张表结构符合 design.md 第 2 节(冗余字段、复合主键、索引、UNIQUE 约束齐全)。
- [ ] AC12: 过期的 session(手动改 expires_at 为过去)访问 /me 返回 401。

## Dependencies

- 无(本子任务为父任务 8 个子任务中的第一个,无前置依赖)。

## Notes

- 本子任务完成后,后续子任务(标签搜索、媒体管道、抓取器、业务路由)都建立在此地基上。
- 模型字段需与父任务 `06-28-gallery-app/design.md` 第 2 节严格一致,后续子任务直接依赖。
