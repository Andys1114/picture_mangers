# Type Safety

> Type safety patterns in this project.

---

## Overview

TypeScript `strict: true` is the contract. The backend exposes Pydantic schemas; the frontend mirrors them as TS interfaces in `lib/types.ts`. The API client (`lib/api.ts`) is typed end-to-end so a backend schema change surfaces as a TS error.

---

## Type Organization

- **`lib/types.ts`** — shared domain types mirroring backend Pydantic response/request shapes: `Post`, `Tag`, `TagImplication`, `Favorite`, `FavoriteItem`, `User`, `SessionSafeMode`, `Paginated<T>`, error envelope `ApiError`.
- **Co-located component prop types** as `<Component>Props` interfaces next to the component.
- **Query key factory** types in `lib/queryClient.ts`.
- Keep types DRY: derive list/paginated wrappers from a base (`Paginated<Post>` rather than a hand-written `PostList`).

---

## Backend Mirror

- Field names and nullability must match the backend Pydantic schema exactly (snake_case → camelCase decision is made once in `lib/api.ts` and applied uniformly; prefer matching the backend's snake_case to avoid drift, or convert at the boundary with a single mapper).
- `Post.duplicate_of_id` is nullable; `Post.fav_count` does **not** exist (do not type it).
- `rating` is the union `'safe' | 'questionable' | 'explicit'`; tag `category` is `'general' | 'character' | 'copyright' | 'artist' | 'meta'`.
- When the backend schema evolves, update `lib/types.ts` in the same change — TS errors elsewhere guide the rest.

---

## Validation

- **No runtime validation library mandated** this milestone — the backend is the trust boundary (auth-gated, single-user). TS types at the API boundary suffice.
- If untrusted input is ever accepted (e.g. user-pasted scrape URLs), validate with **zod** at that entry point and narrow before use. Do not sprinkle zod across trusted internal data flows.
- Parse, don't trust: foreign objects (e.g. from `localStorage`, if ever used) go through a validator before being treated as typed.

---

## Common Patterns

- **Discriminated unions** for variants (tag category → color; task status → `'running' | 'done' | 'failed'`).
- **Type guards** to narrow `unknown` (e.g. when decoding an error envelope: `isApiError(x)`).
- **`as const`** for literal unions and config maps (tag color map).
- **Generics** for the API client: `apiGet<T>(path): Promise<T>`; `Paginated<T>`.

---

## Forbidden Patterns

- **`any`** — use `unknown` + guard, or define the type. `// eslint-disable @typescript-eslint/no-explicit-any` is not a solution.
- **Unchecked `as` assertions** to silence the compiler — fix the type instead. Only assert after a guard that proves the shape.
- **Typing `fav_count`** anywhere — it doesn't exist.
- **Duplicating response shapes** per component — import from `lib/types.ts`.
- **Trusting `unknown` without a guard** (e.g. `JSON.parse` result cast to a type).
