# PM Gallery — Frontend

Next.js 15 (App Router) + TypeScript + Tailwind + shadcn-style UI + TanStack Query.

## Run

```bash
cd frontend
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
