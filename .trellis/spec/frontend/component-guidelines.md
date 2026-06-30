# Component Guidelines

> How components are built in this project.

---

## Overview

Components are React (Next.js App Router). Server Components are used only for static shells/layouts; interactive UI is Client Components. Styling is Tailwind utility classes; complex primitives come from shadcn/ui (source-owned, editable); icons from lucide-react.

---

## Component Structure

- One default-exported component per file; co-located small subcomponents only when tightly coupled.
- **Client Components** (`"use client"`) for anything with state, effects, event handlers, or browser APIs (lightbox, search box, infinite scroll, drag-reorder, safe-mode toggle).
- **Server Components** for static shells (login/setup page wrappers, layout) — no hooks, no interactivity.
- Keep components small and composable; push data logic into hooks (`hooks/`), not into components.

---

## Props Conventions

- Type every prop explicitly with an interface named `<Component>Props`.
- No `any` (see type-safety). Use discriminated unions for variants (e.g. chip color by tag category).
- Prefer narrow, composable props over one giant config object.

---

## Styling Patterns

- **Tailwind utilities** for layout, spacing, color, responsive. No CSS-in-JS, no styled-components.
- **Design tokens** as CSS variables in `styles/globals.css` (dark theme): background levels, text levels, accent, glassmorphism blur/alpha.
- **Tag category colors** are a token map, not ad-hoc:
  - `general` → gray, `character` → blue, `copyright` → purple, `artist` → yellow/amber, `meta` → cyan.
  - Exposed as a `tagCategoryColor(category)` helper returning Tailwind class strings; chips/badges read from it.
- **Glassmorphism** (topbar, info panels): `backdrop-blur` + semi-transparent background + border.
- shadcn/ui primitives are themed via the token CSS variables, not repainted per-use.

---

## Accessibility

- Keyboard navigation is first-class: lightbox `← →` flip, `F` favorite, `E` edit, `Esc` close; focus trap inside modals/lightbox; restore focus on close.
- Every interactive element is a real button/link (no `<div onClick>`); visible focus styles.
- Images need `alt` (post cards: brief alt from tags/source; decorative thumbs: empty alt).
- Color contrast meets WCAG AA on the dark theme (especially the gray `general` tag chip on dark).
- Drag-reorder has a keyboard fallback (arrow keys to move), not pointer-only.

---

## Common Mistakes

- Putting data-fetching/business logic inside a component instead of a hook.
- Hardcoding `/api/...` URLs in components instead of using `lib/api.ts`.
- Repainting shadcn/ui primitives per-use instead of theming via tokens.
- Forgetting `"use client"` on interactive components (hooks won't work).
- Using `<div onClick>` instead of a real button (breaks a11y + keyboard).
