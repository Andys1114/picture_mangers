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

## Backend Endpoint Contract

Frontend slice 1 (skeleton + browse) is wired against the **real** backend —
no frontend mocks for server data (forbidden by `quality-guidelines.md`).
Status of the endpoints the hooks above consume:

**Implemented** (landed with `06-30-frontend-skeleton-browse`):
- `GET /api/auth/status` → `{ setup_required: boolean }` (no auth). Drives `/login` vs `/setup` self-routing.
- `POST /api/auth/setup` `{username, password≥8}` → `UserResponse {id, username}` + sets `gallery_session` cookie. 409 if a user already exists.
- `POST /api/auth/login` `{username, password}` → `UserResponse` + cookie. 401 on bad credentials.
- `POST /api/auth/logout` → 204, clears cookie.
- `GET /api/auth/me` → `MeResponse {id, username, safe_mode}`. 401 without a valid session. **`safe_mode` is per-session and server-authoritative** — read it here, never persist locally.
- `PATCH /api/auth/me/settings` `{safe_mode: boolean}` → `MeResponse`. Toggles the current session's safe_mode; the gallery list refetches with the new rating filter.
- `GET /api/posts?tags=&page=&limit=&order=` → `{data: PostSummary[], meta: {page, total}}`. AND over materialized `post_tags`; `safe_mode=true` (from the session) forces `rating=safe`; duplicates (`duplicate_of_id IS NOT NULL`) excluded; default `order=id` (newest first), `limit` default 40. 401 without session.
- `GET /api/posts/{id}` → `PostDetailResponse` (full fields + expanded `tags: TagResponse[]`). 404 `not_found` if missing.
- `GET /media/...` — static files served by FastAPI `StaticFiles` (same-origin via the Next rewrite). No auth on the static mount.

**Still pending** (later subtasks):
- `GET /api/tags` — tag index with counts (#7).
- `GET /api/tags/tree` — implication tree (#7).
- `GET /api/posts/{id}/next` — prev/next for lightbox flip (#6).
- `GET /api/tasks/{id}` — task progress polling (#8).
- `GET|POST|DELETE /api/favorites`, `/api/favorites/{id}/items` — favorites + drag-reorder (#8). Until then, the post-card ★ is local optimistic visual only (`favorite` is server-fixed to `false`).

> Path note: auth endpoints live under `/api/auth/*` (the auth router prefix), not `/api/*` root. The frontend `lib/api.ts` is the single source of truth for these paths.

Do not build frontend mocks for any pending endpoint — wait for it to land.

---

## Common Mistakes

- Inlining query keys (`['posts']` scattered) instead of a key factory → cache misses/leaks.
- Forgetting to invalidate after mutations → stale UI.
- Using `router.push` for lightbox flip (creates back-hell) instead of `router.replace`.
- Polling forever instead of stopping on terminal status.
