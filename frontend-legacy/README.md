# PM Gallery — Frontend (DEPRECATED / 已废弃)

> **⚠️ 本目录已废弃，仅作存档，不再维护。**
> 2026-07-26 起前端按"暗房霓虹"设计稿在 `../frontend/` 整体重写（决策见
> `docs/adr/0002-frontend-rewrite-keep-legacy.md`，设计稿见
> `docs/design/pm-gallery-redesign/`）。
> 本目录保留用于对照旧行为，仍可手动运行（见下），但**不要**在这里做任何修改；
> `dev.py` 已指向新前端。

Next.js 15 (App Router) + TypeScript + Tailwind + shadcn-style UI + TanStack Query.

## Run

```bash
cd frontend-legacy
npm install
npm run dev          # http://localhost:3000
```

The dev server proxies `/api/*` and `/media/*` to the FastAPI backend
(`http://localhost:8000` by default; override with `BACKEND_URL`). Start the
backend first:

```bash
cd backend
python -m scripts.seed_dev          # creates user admin/pw12345678 + 12 sample posts
uvicorn app.main:app --reload --port 8000
```

## Scripts

- `npm run dev` — dev server
- `npm run build` — production build
- `npm run lint` — eslint
- `npm run typecheck` — `tsc --noEmit`

## Layout

See `.trellis/spec/frontend/directory-structure.md`. `lib/api.ts` is the only
module that knows URLs; components consume hooks, never raw fetch.
