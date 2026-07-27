# Component Guidelines

> How components are built in this project.

---

## Overview

Components are React (Next.js App Router). Server Components are used only for static shells/layouts; interactive UI is Client Components. Styling is Tailwind utility classes; primitives are **self-owned `components/ui/*` (no Radix, no shadcn dependency)** — hand-rolled button/badge/input/dropdown/sheet themed by the token layer (since the 2026-07 "darkroom neon" redesign); icons from lucide-react.

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
- **Single token layer（暗房霓虹）**: every color/radius/easing lives as a CSS variable in `styles/globals.css`, mapped to semantic Tailwind names in `tailwind.config.ts`. **Components never contain hex/rgba/oklch literals** — the only allowed literal-ish class is a black scrim over images (`bg-black/90`). If a new visual needs a value that has no token, add the token first.
- **Glass utilities**: two canonical glass levels are prebuilt classes — `.glass-bar` (bars, 0.72/blur20) and `.glass-pop` (popovers/sheets/cards, 0.92/blur22) — plus ambient-glow background classes (`.bg-ambient`, `.bg-ambient-lightbox`, `.bg-ambient-auth`). Use these; don't hand-compose rgba+blur per component.
- **Tag category & rating colors** come from `lib/colors.ts` as **three-piece chip sets** (15% background + 40% border + light text, per category/rating); chips/badges consume the set via `Badge` + className, never individual color classes.
- **Floating layers** (dropdown, sheet/drawer, popover): shadow comes from the elevation tokens — `shadow-e2`, never raw `shadow-*`; entrance uses the shared animation tokens (`animate-fade-in`, `animate-slide-in-left/right`).
- **Hand-rolled buttons** (anything interactive that isn't shadcn `Button`) carry the four-state baseline: `hover:*`, `active:scale-[0.97]`, `focus-visible:ring-2 focus-visible:ring-accent`, `disabled:opacity-50 disabled:cursor-not-allowed`, plus `transition duration-150 ease-out-soft`, `cursor-pointer`, and `font-medium`. Do NOT use `disabled:pointer-events-none` on menu items — a disabled native button must swallow the click itself so container-level close handlers don't fire through it.
- shadcn/ui primitives are themed via the token CSS variables, not repainted per-use.

## Copy (user-visible text)

- Simplified Chinese, no internal jargon: ticket numbers ("#8"), endpoint names (`GET /api/tags`), or implementation mechanics ("后端按会话注入") never appear in UI copy. Put those in code comments instead.
- Error messages state cause + recovery ("无法连接服务器，请确认后端已启动后重试"), not just "失败".

---

## Accessibility

- Keyboard navigation is first-class: lightbox `← →` flip / `Esc` close, `/` focuses search; focus trap inside modals/lightbox; restore focus on close. (Favorite/edit shortcuts return with their features — favorites UI is deferred by parent-task decision.)
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
- Writing raw hex/rgba/backdrop-blur in a component instead of adding a token / using `.glass-bar`/`.glass-pop`.
- Repainting `components/ui/*` primitives per-use instead of theming via tokens.
- Forgetting `"use client"` on interactive components (hooks won't work).
- Using `<div onClick>` instead of a real button (breaks a11y + keyboard).
