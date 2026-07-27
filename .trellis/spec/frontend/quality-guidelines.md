# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

TypeScript strict, Tailwind + self-owned `components/ui/*` (no Radix/shadcn), TanStack Query. Quality bars: typed API boundary, no `any`, keyboard-accessible interactive UI, dark-theme contrast, no frontend mocks (wait for backend endpoints). Since the 2026-07 redesign, **mobile (<768px) is first-class**: dedicated topbar variant, bottom-sheet filter drawer, lightbox touch gestures.

---

## Forbidden Patterns

- **`any`** — use `unknown` + a type guard, or a proper interface. (See type-safety.)
- **`useEffect` for data fetching** — use TanStack Query hooks.
- **Hardcoded `/api/...` / `http://backend/...` URLs in components** — go through `lib/api.ts`.
- **Frontend mocks for server data** — do not invent mock post/tag data; slice 1 starts after the minimal backend endpoints land.
- **`<div onClick>`** for interactive elements — use a real `<button>`/`<a>` (a11y + keyboard).
- **CSS-in-JS / styled-components** — Tailwind utilities + token CSS variables only.
- **Re-introducing `fav_count` / favorite-count logic on the frontend** — favorite counts are not tracked (backend decision). Derive favorited state from membership.
- **Read-time implication expansion on the frontend** — implications are materialized server-side; the frontend just sends tags and renders results.
- **Running `next build` while the dev server is up** — both write `frontend/.next`; the build clobbers the dev cache mid-flight and the running server starts 500-ing with "module not found in the React Client Manifest" until `.next` is deleted and the server restarted. Verification during dev = `lint` + `tsc --noEmit`; run `next build` only with the dev server stopped.
- **Any favorites/star UI** — deferred whole by parent-task decision 3 (07-26-frontend-redesign); backend endpoints stay, UI must not surface them until the dedicated task.

---

## Required Patterns

- **TypeScript `strict: true`**; no implicit any, no unchecked index access where avoidable.
- **Typed API layer**: `lib/api.ts` returns typed `Promise<T>`; components consume hooks, never raw fetch.
- **`"use client"`** on any component using hooks/handlers/browser APIs.
- **Query key factory** in `lib/queryClient.ts`; mutations invalidate via the factory.
- **Keyboard parity** for every pointer interaction (lightbox nav, drag-reorder, drawer).
- **Design tokens** for color/spacing; tag category & rating colors via the `lib/colors.ts` three-piece chip sets (see component-guidelines).
- **Accessible images**: `alt` on post cards; explicit `width`/`height` to prevent layout shift (values from `Post.width/height`).

---

## Testing Requirements

- Component/logic tests with Vitest (+ React Testing Library) for non-trivial logic (lightbox close-strategy, query key factory, tag color map, optimistic rollback).
- E2E (Playwright) for the critical path: login → browse → open lightbox → flip → close → back-button behavior.
- Type-check (`tsc --noEmit`) and lint (`eslint`) must be green before a slice is reported done.
- Run from `frontend/` so the TS project config applies.

---

## Responsive Scope

- Breakpoints: masonry lg≥1024 → 4 cols, md≥768 → 3 cols, below → 2 cols. Desktop-only chrome (filter rail, lightbox nav buttons) hides with `max-md:hidden`; mobile chrome (46px topbar variant, chips row, bottom-sheet drawer, lightbox gestures + bottom half-layer) mounts under the same breakpoint. Desktop rail and mobile drawer share the same content components (`rail-tags`/`rail-ratings`/`rail-chips`) — never fork them.
- Touch gestures go through Pointer Events with **axis-dominance judgment** (`|dx| > |dy|`), pointer capture on down, and a swallowed synthetic click after a recognized swipe (else the swipe also "clicks" whatever is under the finger).
- Flex children that must shrink (e.g. the topbar search form) need explicit `min-w-0` — the `min-width: auto` default is the usual 375px-overflow culprit.

## Known Deferred (recorded, do not re-report)

- **List virtualization** for the infinite waterfall (masonry-grid keeps all loaded cards in the DOM). Architectural; revisit when libraries have thousands of posts.
- **Waterfall tab order is column-major** (greedy column split): DOM order follows columns, not visual rows. Inherent to the layout; acceptable for a gallery.
- The masonry layout is JS greedy-split flex columns (prefix-stable so appended pages never move rendered cards) — do NOT "simplify" it back to CSS `column-count`; that reflows every card on each appended page.

---

## Code Review Checklist

- [ ] No `any`; API boundary typed via `lib/types.ts`.
- [ ] Data via TanStack Query hooks, not `useEffect`+fetch.
- [ ] No hardcoded API/media URLs (use `lib/api.ts` + rewrite).
- [ ] Interactive elements are real buttons/links; keyboard parity.
- [ ] Lightbox uses push/replace/back correctly (no back-hell; direct-link close strips param).
- [ ] `safe_mode` not persisted locally; reflects `/api/me`.
- [ ] Dark-theme contrast OK; tag colors via token map.
- [ ] `tsc --noEmit` + eslint green; tests for non-trivial logic.
