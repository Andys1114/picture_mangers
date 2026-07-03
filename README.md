# Picture Mangers

类 Danbooru 现代画廊图库应用：本地导入 + Danbooru 抓取，深色沉浸式画廊 UI，标签系统（分类着色 + implication 树），安全模式，收藏夹，单用户登录。Next.js + FastAPI + SQLite。

## 一键启动（开发）

```bash
python dev.py
```

启动后：

- **画廊前端** → http://localhost:3000（`/api` 与 `/media` 由 Next.js rewrite 代理到后端，同源）
- **后端 API** → http://localhost:8000（交互文档 `/docs`，健康检查 `/api/health`）
- 首次启动会自动跑 Alembic 迁移 + `seed_dev`（建单用户 `admin` / `pw12345678` + 12 张示例图）

`Ctrl+C` 同时停止前后端。跳过 seed 加 `--no-seed`。

### 前置依赖

- **后端**：Python 3.11+，依赖见 `backend/pyproject.toml`（fastapi / sqlalchemy / alembic / pillow / imagehash / apscheduler 等）。在装好这些依赖的解释器里跑 `dev.py`。
- **前端**：Node 18+，先在 `frontend/` 跑过 `npm install`（`node_modules` 存在即可）。

### 端口 / 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `BACKEND_PORT` | `8000` | 后端 uvicorn 端口 |
| `PORT` | `3000` | 前端 Next.js 端口 |
| `BACKEND_URL` | `http://localhost:8000` | 前端 rewrite 的后端目标（改端口时同步改） |

## 项目结构

```
picture_mangers/
├── dev.py                 一键启动（前后端同跑 + Ctrl+C 同停）
├── backend/               FastAPI + SQLAlchemy + SQLite(WAL) + Alembic
│   ├── app/               api / services / models / schemas / scrapers
│   ├── alembic/           迁移
│   └── scripts/seed_dev.py  开发造数
├── frontend/              Next.js 15 (App Router) + TS + Tailwind + TanStack Query
└── docs/adr/              架构决策记录
```

## 测试

```bash
cd backend && python -m pytest -v   # 63 例
```

## 已知约束

- **Danbooru 抓取受 Cloudflare 403 拦截**：`scrapers/danbooru.py` 按 API 文档实现，但真实抓取在本机不可行（JS challenge）。配 `HTTPS_PROXY` 后 httpx 自动走代理，代码无需改。导入页的本地扫描（`POST /api/import/scan`）完全可用。
