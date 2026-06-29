# 后端骨架 — 技术设计

> 父任务设计:`06-28-gallery-app/design.md`。本文件聚焦子任务 1 的边界、契约、技术取舍。

---

## 1. 模块边界

```
backend/app/
├── main.py              FastAPI 应用入口
├── config.py            Settings (pydantic-settings)
├── db.py                engine + SessionLocal + get_db 依赖
├── models/
│   ├── __init__.py      导出全部模型 (供 Alembic autogetect)
│   ├── base.py          DeclarativeBase
│   ├── user.py          User, Session
│   ├── post.py          Post
│   ├── tag.py           Tag, PostTag, TagImplication
│   └── favorite.py      Favorite, FavoriteItem
├── schemas/
│   ├── auth.py          SetupRequest, LoginRequest, UserResponse, StatusResponse
│   └── common.py        ErrorResponse, Envelope
├── api/
│   ├── __init__.py      APIRouter 聚合
│   ├── health.py        GET /api/health
│   └── auth.py          /setup /login /logout /me /status
├── services/
│   ├── auth.py          密码哈希、session 签发/校验
│   └── errors.py        异常 → 信封转换
└── deps.py              get_current_user 依赖
```

### 职责分层
- **api/** — 只做请求解析、调用 service、返回响应。不含业务逻辑。
- **services/** — 业务逻辑(密码哈希、session 管理)。可被多个 api 复用。
- **models/** — 纯 ORM 定义,无业务方法。
- **deps.py** — FastAPI 依赖(get_db、get_current_user),横切关注点。

## 2. 关键契约

### 认证状态机
```
DB 无 user:
  GET  /api/auth/status  → {setup_required: true}
  POST /api/auth/setup   → 创建 user + 签发 session (200)
  POST /api/auth/setup   (已有 user) → 409 Conflict

DB 有 user:
  GET  /api/auth/status  → {setup_required: false}
  POST /api/auth/login   (密码对) → 200 + Set-Cookie
  POST /api/auth/login   (密码错) → 401

已登录 (有效 cookie):
  GET  /api/auth/me      → 200 {id, username}
  POST /api/auth/logout  → 204 + Clear-Cookie

无/失效 cookie:
  GET  /api/auth/me      → 401
```

### Cookie 规范
- 名:`gallery_session`
- 值:session token (secrets.token_urlsafe(32))
- `HttpOnly=True`(防 XSS 读)
- `SameSite=Lax`
- `Secure`:生产(True),开发可 False
- `Path=/`
- 过期:sessions.expires_at(默认 30 天)

### 统一错误信封
所有非 2xx 返回:
```json
{"error": {"code": "invalid_credentials", "message": "用户名或密码错误"}}
```
HTTP 状态码:400(请求错误)/ 401(未认证)/ 409(冲突)/ 500(服务器错误)。

## 3. 数据库初始化细节

### 启动 pragma(WAL + 外键)
在 `db.py` 的 engine 事件监听器里,每次连接初始化时执行:
```python
from sqlalchemy import event

@event.listens_for(engine, "connect")
def _set_pragma(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.close()
```

### Alembic 配置
- `alembic.ini` 指向 `app.db` 的 engine url(从 config 读)。
- `alembic/env.py` 导入 `app.models` 全部模型 + 设置 `target_metadata`。
- 初始 migration(`alembic revision --autogenerate`)生成全部 8 表。
- migration 独立于运行时建表:不在 main.py 里 `create_all`,全部走 Alembic。

## 4. 配置项(config.py)

| 项 | 默认 | 说明 |
|---|---|---|
| `database_url` | `sqlite:///./picture_mangers.db` | DB 路径 |
| `media_dir` | `./media` | 媒体存储目录 |
| `secret_key` | (env 必填或随机) | session 签名相关 |
| `cors_origins` | `["http://localhost:3000"]` | 前端 origin |
| `session_expire_days` | `30` | session 有效期 |
| `secure_cookie` | `False`(开发) | cookie Secure 标志 |

用 `pydantic-settings` 的 `BaseSettings`,从 `.env` 或环境变量读。

## 5. 测试策略

- 用 `pytest` + `httpx` 的 ASGITransport(内存测试,不占真实端口)。
- 每个测试用独立临时 SQLite 文件(fixture 提供)。
- 测试覆盖 AC1-AC12 全部验收点。
- 认证状态机用参数化测试覆盖所有分支。

## 6. 取舍与兼容

- **不用 create_all,用 Alembic** — 为后续 schema 演进(加字段/索引)铺路,子任务 2-8 会频繁改表。
- **session 存 DB 而非 JWT** — 个人图库,无状态 JWT 的优势用不上;DB session 可主动失效(logout 即删记录),实现简单。
- **密码 bcrypt cost=12** — 平衡安全与性能。
- **不放业务路由** — 本子任务严格只做地基,posts/tags 路由留给后续,避免范围蔓延。
