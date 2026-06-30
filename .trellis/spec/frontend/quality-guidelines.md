# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

TypeScript strict, Tailwind + shadcn/ui, TanStack Query. Quality bars: typed API boundary, no `any`, keyboard-accessible interactive UI, dark-theme contrast, no frontend mocks (wait for backend endpoints). This milestone is desktop-first with narrow-screen grace; mobile touch is out of scope.

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

---

## Required Patterns

- **TypeScript `strict: true`**; no implicit any, no unchecked index access where avoidable.
- **Typed API layer**: `lib/api.ts` returns typed `Promise<T>`; components consume hooks, never raw fetch.
- **`"use client"`** on any component using hooks/handlers/browser APIs.
- **Query key factory** in `lib/queryClient.ts`; mutations invalidate via the factory.
- **Keyboard parity** for every pointer interaction (lightbox nav, drag-reorder, drawer).
- **Design tokens** for color/spacing; tag category color via the `tagCategoryColor` map.
- **Accessible images**: `alt` on post cards; explicit `width`/`height` to prevent layout shift (values from `Post.width/height`).

---

## Testing Requirements

- Component/logic tests with Vitest (+ React Testing Library) for non-trivial logic (lightbox close-strategy, query key factory, tag color map, optimistic rollback).
- E2E (Playwright) for the critical path: login → browse → open lightbox → flip → close → back-button behavior.
- Type-check (`tsc --noEmit`) and lint (`eslint`) must be green before a slice is reported done.
- Run from `frontend/` so the TS project config applies.

---

## Responsive Scope

- **Desktop-first** this milestone. Breakpoints: waterfall column count scales with viewport; topbar/drawer adapt.
- **Narrow-screen grace**: layout must not break/overflow below ~768px, but no dedicated mobile touch UX (drag-reorder may be desktop-only with a keyboard fallback).
- **Dedicated mobile** is deferred to a later version.

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
