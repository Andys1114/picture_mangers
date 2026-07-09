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
  - ⚠ When wiring tag chips: `text-accent` on dark surfaces fails 4.5:1 since `--accent` was deepened to #2563eb (button contrast). Use a light text variant (`text-blue-300`, matching the other categories' `*-300` pattern).
- **Glassmorphism** (topbar, info panels): `backdrop-blur` + semi-transparent background + border.
- **Floating layers** (dropdown, sheet/drawer, popover): shadow comes from the elevation tokens — `shadow-e2`, never raw `shadow-*`; entrance uses the shared animation tokens (`animate-fade-in`, `animate-slide-in-left/right`).
- **Hand-rolled buttons** (anything interactive that isn't shadcn `Button`) carry the four-state baseline: `hover:*`, `active:scale-[0.97]`, `focus-visible:ring-2 focus-visible:ring-accent`, `disabled:opacity-50 disabled:cursor-not-allowed`, plus `transition duration-150 ease-out-soft`, `cursor-pointer`, and `font-medium`. Do NOT use `disabled:pointer-events-none` on menu items — a disabled native button must swallow the click itself so container-level close handlers don't fire through it.
- shadcn/ui primitives are themed via the token CSS variables, not repainted per-use.

## Copy (user-visible text)

- Simplified Chinese, no internal jargon: ticket numbers ("#8"), endpoint names (`GET /api/tags`), or implementation mechanics ("后端按会话注入") never appear in UI copy. Put those in code comments instead.
- Error messages state cause + recovery ("无法连接服务器，请确认后端已启动后重试"), not just "失败".

---

## Accessibility

- Keyboard navigation is first-class: lightbox `← →` flip, `F` favorite, `E` edit, `Esc` close; focus trap inside modals/lightbox; restore focus on close.
- Modal layers follow the `Sheet` reference implementation: focus moves in on open, Tab is trapped (with an empty-focusable guard), focus restores to the opener on close, body scroll is locked while open, and a visible close button exists alongside Esc + backdrop click. `html { scrollbar-gutter: stable }` keeps the scroll-lock from shifting the page.
- Anything revealed on `group-hover` must also reveal on `group-focus-within` (keyboard parity); fixed bars that hide on scroll must reveal on `focus-within` so Tab never lands in invisible controls.
- Every interactive element is a real button/link (no `<div onClick>`); visible focus styles (ring + `ring-offset-background` on fields).
- Images need `alt` (post cards: brief alt from tags/source; decorative thumbs: empty alt). Decorative lucide icons always get `aria-hidden` (the library doesn't add it).
- Toggle buttons keep a **stable** `aria-label` (e.g. "安全模式") and express state via `aria-pressed` — don't flip the label text with the state.
- `aria-invalid` only on fields the error actually implicates (client validation → that field; network failure → none), never blanket `!!error` on every input.
- Color contrast meets WCAG AA on the dark theme (especially the gray `general` tag chip on dark). Text over images sits on a scrim of at least `bg-black/90` at chip size, or a gradient computed against a white-image worst case.
- Drag-reorder has a keyboard fallback (arrow keys to move), not pointer-only.

---

## Common Mistakes

- Putting data-fetching/business logic inside a component instead of a hook.
- Hardcoding `/api/...` URLs in components instead of using `lib/api.ts`.
- Repainting shadcn/ui primitives per-use instead of theming via tokens.
- Forgetting `"use client"` on interactive components (hooks won't work).
- Using `<div onClick>` instead of a real button (breaks a11y + keyboard).
