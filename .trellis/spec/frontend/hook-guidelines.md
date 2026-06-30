# Hook Guidelines

> How hooks are used in this project.

---

## Overview

Custom hooks live in `hooks/`, named `use*`, one per file. Data fetching, mutations, polling, and cache invalidation all go through TanStack Query (React Query) — no `useEffect`+`fetch` reimplementations.

---

## Custom Hook Patterns

- **Resource hooks** wrap a TanStack Query call and return `{ data, isLoading, error, ... }`:
  - `useInfinitePosts({ tags, rating })` — `useInfiniteQuery`, waterfall pagination.
  - `usePost(id)` — `useQuery` for single post (lightbox direct-link mode).
  - `useMe()` — current user + session `safe_mode`.
  - `useTags()` — tag index (by category, with counts).
  - `useTask(id)` — `useQuery` + `refetchInterval` polling for import/scrape progress.
- **Mutation hooks** wrap `useMutation` with optimistic update + invalidation:
  - `useToggleFavorite()`, `useUpdatePostTags()`, `useReorderFavorite()`, `useUpdateSafeMode()`.
- Keep query keys centralized in `lib/queryClient.ts` (a key factory) — never inline string keys.

---

## Data Fetching

- **All API data via TanStack Query** — caching, dedupe, retry, stale-while-revalidate come for free.
- `useInfiniteQuery` for the waterfall: `getNextPageParam` from the backend's pagination cursor; `IntersectionObserver` (via a sentinel + `fetchNextPage`) triggers the next page.
- **Polling** for long tasks: `useQuery({ queryKey: ['task', id], queryRefetchInterval: (q) => q.state.data?.status === 'done' || 'failed' ? false : 1000 })`.
- **Optimistic updates**: mutations roll back on error; on success, invalidate affected keys (e.g. after `useUpdateSafeMode`, invalidate `['posts']` so lists refetch with the new rating filter).
- No `useEffect` for fetching. `useEffect` only for non-data side effects (subscriptions, DOM measurements).

---

## Lightbox Hook

- `useLightbox()` reads `useSearchParams()` for `photoId`; exposes `open(id)` (router.push, scroll:false), `flipTo(id)` (router.replace, no back-hell), `close()` (back if opened in-session, else replace to strip param — see CONTEXT.md "详情页(Lightbox)"). Records `wasOpenOnMount` to choose close strategy.

---

## Naming Conventions

- `use<Resource>` for queries (`usePost`, `useTags`).
- `use<Action><Resource>` for mutations (`useUpdateSafeMode`, `useToggleFavorite`).
- `useInfinite<Resource>` for paginated lists.

---

## Backend Endpoint Contract (pending)

These backend endpoints are required by the hooks above and are **not yet implemented** (tracked in the parent task's pending list):
- `GET /api/posts?tags=&rating=&page=&limit=` — list, AND filter, rating filter, default-exclude duplicates, `safe_mode` injected from session.
- `GET /api/posts/{id}` — single post (lightbox direct-link).
- `GET /api/tags` — tag index with counts.
- `GET /api/me` — user + current session `safe_mode`.
- `PATCH /api/me/settings { safe_mode }` — update current session's safe_mode.
- `GET /api/auth/status` — `{ owner_exists }` (no auth).
- `GET /api/tasks/{id}` — task progress (import/scrape).
- `GET|POST|DELETE /api/favorites`, `/api/favorites/{id}/items` — favorites + drag-reorder.

Do not build frontend mocks — frontend slice 1 starts after the minimal backend endpoints (`/api/posts`, `/api/posts/{id}`, `/api/auth/status`, `/api/me`, StaticFiles `/media`) land.

---

## Common Mistakes

- Inlining query keys (`['posts']` scattered) instead of a key factory → cache misses/leaks.
- Forgetting to invalidate after mutations → stale UI.
- Using `router.push` for lightbox flip (creates back-hell) instead of `router.replace`.
- Polling forever instead of stopping on terminal status.
