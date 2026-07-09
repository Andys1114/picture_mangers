# Directory Structure

> How frontend code is organized in this project.

---

## Overview

The frontend is a standalone Next.js 15 (App Router) app living under `frontend/`, a separate process from the FastAPI backend. It calls the backend over HTTP (same-origin via a rewrite, see below). Stack: TypeScript + Tailwind CSS + shadcn/ui + lucide-react + TanStack Query.

---

## Directory Layout

```
frontend/
├── app/                      Next.js App Router
│   ├── (protected)/          route group requiring session cookie (guarded by middleware)
│   │   ├── page.tsx          /  — browse (waterfall + topbar + search + safe-mode + tag drawer)
│   │   ├── tags/page.tsx     /tags
│   │   ├── favorites/        /favorites, /favorites/[id]
│   │   ├── import/page.tsx   /import
│   │   ├── scrape/page.tsx   /scrape
│   │   └── settings/page.tsx /settings
│   ├── login/page.tsx        /login  (public)
│   ├── setup/page.tsx        /setup  (public)
│   ├── layout.tsx            root layout: providers (TanStack QueryClient), theme
│   └── middleware.ts (see note)
├── middleware.ts             cookie-presence gate — Next.js requires this at the project root, NOT under app/. File shown here for layout overview; the real file is frontend/middleware.ts.
├── components/
│   ├── ui/                   shadcn/ui components (source-owned, editable)
│   ├── browse/               waterfall, card, topbar, search-box, tag-drawer, safe-mode-toggle
│   ├── lightbox/             lightbox overlay (driven by ?photoId)
│   ├── tags/                 tag list, implication tree, tag chip
│   ├── favorites/            favorite list, drag-reorder
│   └── common/               shared layout primitives
├── hooks/                    custom hooks (usePosts, usePost, useInfinitePosts, useMe, ...)
├── lib/
│   ├── api.ts                typed fetch client + endpoint definitions
│   ├── types.ts              TS interfaces mirroring backend Pydantic schemas
│   └── queryClient.ts        TanStack Query client + key factory
├── styles/
│   └── globals.css           Tailwind base + design tokens (CSS variables)
├── public/
├── next.config.ts            rewrites: /media/* → backend /media/* (same-origin)
└── package.json
```

---

## Module Organization

- **One feature folder per page cluster** under `components/` (browse, lightbox, tags, favorites). Cross-feature bits go in `common/`.
- **`lib/api.ts` is the only place that knows URLs** — components/hooks import typed functions, never hardcode `/api/...` strings.
- **shadcn/ui components live in `components/ui/`** and are source-owned (added via `shadcn add`, then freely edited).
- **Route group `(protected)`** groups auth-required routes so middleware logic is obvious; `login`/`setup` stay public.

---

## Naming Conventions

- Files: `kebab-case.tsx` for components when multi-word; route files follow Next.js (`page.tsx`, `layout.tsx`, `middleware.ts`).
- Components: `PascalCase`. Hooks: `useThing` (camelCase, prefix `use`).
- Custom hooks in `hooks/`, one per file, named after the resource/behavior (`useInfinitePosts`, `usePost`, `useMe`, `useUpdateSafeMode`).

---

## Cross-Origin / Media

The frontend reaches the backend same-origin via a Next.js rewrite in `next.config.ts`:
- `/media/*` → `http://<backend>/media/*` (images served by FastAPI StaticFiles).
- API calls go to `/api/*` (also rewritten, or called directly on the backend origin — picked at implementation time; same-origin preferred).

This keeps all frontend URLs same-origin; the browser's HttpOnly session cookie travels automatically.

---

## Examples

- Browse page + lightbox: `app/(protected)/page.tsx` + `components/lightbox/`.
- Typed API client + backend-mirrored types: `lib/api.ts` + `lib/types.ts`.
