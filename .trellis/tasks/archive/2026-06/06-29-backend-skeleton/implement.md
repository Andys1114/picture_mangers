# 后端骨架 — 执行计划

> 依序执行,每个阶段有验证命令。Review gate 在关键节点。

---

## 阶段 1:项目脚手架与依赖

### 步骤
1. 创建 `backend/` 目录结构(按 design.md 第 1 节)。
2. 写 `backend/pyproject.toml`:核心依赖 fastapi、uvicorn[standard]、sqlalchemy>=2.0、alembic、pydantic-settings、bcrypt、python-multipart。
3. 写 `backend/requirements.txt`(从 pyproject 导出固定版本)。
4. 写 `.gitignore`(忽略 venv、__pycache__、*.db、media/)。
5. 写 `backend/app/__init__.py`(空)。

### 验证
```bash
cd backend && python -c "import fastapi, sqlalchemy, alembic, bcrypt; print('deps ok')"
```

---

## 阶段 2:配置与数据库层

### 步骤
1. `app/config.py`:pydantic-settings BaseSettings,字段按 design.md 第 4 节。
2. `app/db.py`:engine(从 config.database_url)、SessionLocal、`get_db` 依赖、connect 事件监听器设 WAL/foreign_keys/synchronous pragma。
3. 初始化 Alembic:`cd backend && alembic init alembic`。
4. 配 `alembic.ini` 的 sqlalchemy.url(从环境变量读,不硬编码)。
5. 配 `alembic/env.py`:导入 `app.models` 全部、设 `target_metadata = Base.metadata`。

### 验证
```bash
cd backend && python -c "from app.db import engine; print(engine.url)"
```

---

## 阶段 3:ORM 模型(8 表)

### 步骤
1. `app/models/base.py`:DeclarativeBase + 公共 TimestampMixin(created_at/updated_at)。
2. `app/models/user.py`:User(id, username UNIQUE, password_hash, timestamps)、Session(id TEXT PK, user_id FK, expires_at)。
3. `app/models/post.py`:Post(按 design.md 第 2 节全部字段,含 is_duplicate、fav_count、三档 path)。
4. `app/models/tag.py`:Tag(name UNIQUE, category, post_count, is_deprecated)、PostTag(复合主键 + tag_id 索引)、TagImplication(antecedent/consequent FK + UNIQUE)。
5. `app/models/favorite.py`:Favorite(name, timestamps)、FavoriteItem(复合主键 + position)。
6. `app/models/__init__.py`:导出全部模型(供 Alembic autogenerate)。

### 生成 migration
```bash
cd backend && alembic revision --autogenerate -m "initial schema"
```
检查生成的 migration 文件,确认 8 表 + 索引/约束齐全。

### 验证
```bash
cd backend && alembic upgrade head
sqlite3 picture_mangers.db ".tables"   # 应见 8 张表 + alembic_version
sqlite3 picture_mangers.db "PRAGMA journal_mode"   # wal
sqlite3 picture_mangers.db "PRAGMA foreign_keys"   # 1
```

---

## 阶段 4:认证 service 与 schemas

### 步骤
1. `app/schemas/common.py`:Envelope、ErrorResponse。
2. `app/schemas/auth.py`:SetupRequest、LoginRequest、UserResponse、StatusResponse。
3. `app/services/auth.py`:
   - `hash_password(pw)` / `verify_password(pw, hash)`(bcrypt cost=12)
   - `create_session(db, user)` → 返回 token(secrets.token_urlsafe(32))+ 写 sessions 表(过期 = now + config.session_expire_days)
   - `validate_session(db, token)` → 查 sessions 表,过期返 None,否则返 user
4. `app/deps.py`:`get_current_user` 依赖,从 cookie `gallery_session` 读 token,调 validate_session,失败 raise 401。

### 验证
```bash
cd backend && python -c "from app.services.auth import hash_password, verify_password; h=hash_password('test'); print(verify_password('test', h), verify_password('x', h))"
```

---

## 阶段 5:API 路由

### 步骤
1. `app/api/health.py`:`GET /api/health` → {status:"ok"}(无认证)。
2. `app/api/auth.py`:
   - `GET /api/auth/status` → {setup_required: <db 无 user>} (无认证)
   - `POST /api/auth/setup` → 仅 db 无 user 时可用,创建 user + 签发 session + Set-Cookie;已有 user 返 409
   - `POST /api/auth/login` → bcrypt 校验,签发 session + Set-Cookie;错密码 401
   - `POST /api/auth/logout` → 删当前 session 记录 + Clear-Cookie
   - `GET /api/auth/me` → 当前用户(需 get_current_user)
3. `app/api/__init__.py`:聚合 router。
4. `app/services/errors.py`:自定义异常 + 全局 exception_handler → 统一错误信封。
5. `app/main.py`:创建 FastAPI app,挂 CORS 中间件、API router、exception handlers。

### 验证(手动冒烟)
```bash
cd backend && uvicorn app.main:app --reload
# 另一终端:
curl localhost:8000/api/health
curl localhost:8000/api/auth/status
curl -X POST localhost:8000/api/auth/setup -H "Content-Type: application/json" -d '{"username":"admin","password":"pw"}'
curl -X POST localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"pw"}' -c cookies.txt
curl --cookie cookies.txt localhost:8000/api/auth/me
```

---

## 阶段 6:测试

### 步骤
1. `backend/tests/conftest.py`:fixtures — 临时 SQLite、TestClient、清库。
2. `backend/tests/test_health.py`:AC2。
3. `backend/tests/test_auth.py`:覆盖 AC3-AC8、AC12(过期 session)。
4. `backend/tests/test_schema.py`:AC9-AC11(表结构、WAL、foreign_keys)。

### 验证
```bash
cd backend && pytest -v
```
全部 AC1-AC12 通过。

---

## Review Gates

- **Gate A**(阶段 3 后):检查 autogenerate 的 migration,确认 8 表字段/索引/约束与 design.md 一致。若有缺漏,改模型后重新 autogenerate。
- **Gate B**(阶段 5 后):手动冒烟全通过,认证状态机各分支行为正确。
- **Gate C**(阶段 6 后):pytest 全绿,AC1-AC12 全覆盖。

## 回滚点

- 阶段 3 migration 出错 → 删 migration 文件,改模型重新生成。
- 阶段 5 路由逻辑错乱 → 回退到阶段 4 的 service(已验证),重新写路由。
- DB 状态污染 → 删 `picture_mangers.db` + `alembic downgrade base` 重来。

## 完成判定

- AC1-AC12 全部通过。
- `backend/` 结构符合 design.md 第 1 节。
- pytest 全绿。
- 代码符合 `.trellis/spec/backend/` 规范(若已填;空则按通用 Python 规范)。
