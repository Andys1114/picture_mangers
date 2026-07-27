# State Management

> How state is managed in this project.

---

## Overview

State is split by category: **server state** in TanStack Query, **URL state** for things that must survive refresh/share (lightbox `photoId`, search query), **local UI state** in React `useState` for ephemeral UI (drawer open, edit mode). No Redux/Zustand — the app doesn't need global client state beyond server state + URL.

---

## State Categories

- **Server state** (posts, tags, favorites, me, tasks): TanStack Query is the single source of truth. Components never hold a server copy in local state.
- **URL state** (Next.js `useSearchParams` / `router`):
  - `?photoId=<id>` — active lightbox (see CONTEXT.md "详情页(Lightbox)").
  - `?tags=a+b` — active search, space-separated AND (shareable, refresh-stable).
  - `?ratings=safe,questionable` — comma-joined explicit rating subset; **full selection / empty = no param** (server treats absent as "all"; safe mode overrides server-side anyway).
- **Local UI state** (`useState` / component state): drawer open/closed, drag-in-progress, hover controls. Ephemeral, not persisted. Exception: filter-rail pin state persists in `localStorage("rail_pinned")` — pure device preference, never server data.
- **Session-derived state** (`safe_mode`): comes from the backend session via `useMe()` (`GET /api/auth/me`); **not** stored in localStorage. Toggling calls `useUpdateSafeMode` (`PATCH /api/auth/me/settings`) then invalidates the posts list.

---

## Pattern: One Hook Owns a URL Contract

**Problem**: multiple components (search box, rail chips, drawer, no-results suggestions) read/write the same filter params; scattered `router.replace` calls drift on serialization details (when to omit the param, how to join values, which history op).

**Solution**: a single hook (`components/browse/use-filter-params.ts`) owns the read (parse + normalize) and every write path (`setTags` / `toggleTag` / `removeTag` / `toggleRating` / `removeRating` / `clearAll`). Consumers never touch `URLSearchParams` for these keys.

**History-op rules** (the part people get wrong):
- Filter changes → `router.replace({ scroll: false })` — filters are *refinements*, they must not stack history entries.
- Lightbox open → `push` (back button must close it); flip → `replace`; close → `history.back()` **only if opened in-session**, else replace the param away (direct-entry back would leave the site). The in-session flag must live in a component that stays mounted across the overlay's lifetime — measured inside the overlay it is always "direct".
- Writers preserve unrelated params (`photoId` survives filter edits and vice versa).

**Why**: URL stays the single source of truth (refresh/share/back all work), and serialization edge cases ("all selected = no param") are decided exactly once.

---

## When to Use Global State

- Default: don't. Local + URL + server state cover the app.
- A React Context is acceptable for cross-tree concerns that aren't server data: e.g. a `ThemeProvider` (dark), a `QueryClientProvider`, maybe a `SafeModeProvider` that wraps `useMe` for synchronous read. No state library.

---

## Server State

- TanStack Query client in `lib/queryClient.ts`, provided in the root layout.
- Query keys via a factory (`['posts', { tags, rating }]`, `['post', id]`, `['me']`).
- Stale time / gc time tuned per resource (posts: short stale; tags: long; me: invalidation-driven).
- Mutations invalidate the minimum necessary keys (e.g. favorite toggle → invalidate `['post', id]` + `['favorites']`, not everything).

---

## Safe-Mode Lifecycle

`safe_mode` is **per-session**, stored on the backend `Session` (default `true` on new session/login). The frontend:
1. `useMe()` reads it on app load and renders the toggle.
2. Toggle → `useUpdateSafeMode` (optimistic flip + `PATCH /api/auth/me/settings`).
3. On success → invalidate the posts list (via the `postsAll()` key factory prefix) so it refetches with the new filter.
4. New login → backend new session → `safe_mode=true` again (auto-revert). The frontend just reflects whatever `/api/auth/me` returns.

Do not persist safe_mode in localStorage or URL — it is server-authoritative.

---

## Common Mistakes

- Copying server data into `useState` and editing the copy → divergence.
- Putting `photoId`/`tags` in local state instead of URL → breaks refresh/share/back button.
- Persisting `safe_mode` locally → drifts from backend session.
- Reaching for Redux/Zustand for something TanStack Query + URL state already covers.
