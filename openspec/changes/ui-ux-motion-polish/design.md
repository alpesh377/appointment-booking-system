# Design

## Context

The frontend is Next.js 15 App Router + React 19, Tailwind CSS 4 with CSS-first tokens, shadcn/ui-style primitives under `src/components/ui`, React Query (`@tanstack/react-query`) for data, `react-hook-form` + `zod` for forms, and `motion` (`motion/react`) already installed. `motion.tsx` currently holds only `FadeIn`, mounted under a `MotionConfig reducedMotion="user"` provider. Backend and API contracts are untouched by this change.

## Approach

### 1. Primitives (shadcn add)

- `npx shadcn@latest add skeleton sonner toast empty tabs separator` (copy-in; check each uses Tailwind v4 tokens from our `globals.css`, no JS config).
- Mount `Toaster` (sonner) once in `src/app/layout.tsx`, styled with our tokens (`richColors=false`, themed background), and expose a tiny wrapper `components/ui/toast.tsx` exporting `toastSuccess` / `toastError` helpers so pages call a consistent API and copy conventions stay uniform.

### 2. Motion toolkit (`components/motion.tsx`)

Keep everything on `motion/react`, all gated by `useReducedMotion()`:

- `StaggerGroup` / `StaggerItem` — grid and list entrances (opacity + y, 0.2s, ≤0.04s stagger, capped so late items aren't delayed noticeably).
- `Pressable` — active-scale (≈0.98) wrapper for cards/slot buttons; passive hover lift.
- `Swap` — `AnimatePresence mode="popLayout"` wrapper for lists whose keys re-query (search results, slot grid, filtered tables).
- `SelectionHighlight` — shared `layoutId` pill that slides between selected items (slot picker tabs).
- `StatusBadge` — animated status change (badge swap with a short y-flip) for appointment status transitions.

Rules: no layout-triggering animations on route navigation; nothing animates larger than a card; all durations < 300ms.

### 3. Pages

- **Provider listing** (`app/page.tsx`): debounced (300ms) live search from the existing `term` state — `query` updates from an effect, so Enter/submit stays harmless; results skeleton grid (skeleton cards reuse the provider card's layout); results count line with `aria-live="polite"`; `Swap` around the grid; `Pressable` + hover lift on cards; `Empty` component with "Browse providers" CTA for empty states.
- **Booking** (`app/providers/[id]/book/page.tsx`): slot grid gains `SelectionHighlight` + `Pressable` and time-of-day grouping (Morning < 12:00, Afternoon 12:00–17:00, Evening ≥ 17:00 in the provider's timezone — grouping is presentation only, computed from the slot ISO string); slots wrapped in `Swap` keyed by `serviceId|date`; sticky summary aside (`lg:sticky top-*`) showing provider/service/duration/date/time; submit button receives the shared `Loading`-style spinner inline; on success `toastSuccess` then redirect (existing behavior kept). Failure keeps the existing alert AND adds `toastError`.
- **Provider dashboard** (`app/provider/page.tsx`, `services`, `availability`): skeleton sections per query; every mutation `onSuccess` → `toastSuccess` with the record name; appointments list gets optimistic updates via React Query's `onMutate` cache patch + rollback `onError` (+ `toastError`) and `invalidateQueries` on settle.
- **Admin** (`app/admin/*`): same treatment — skeletons, toasts, optimistic row updates for deactivate/reactivate and cancel; filters stay server-driven.
- **Appointment detail** (`app/appointments/[id]/page.tsx`): `StatusBadge` for status transitions; cancel/reschedule actions toast when they succeed/fail.
- **Profile & auth pages**: only consistency touches (skeleton, empty states) — no flow changes.

### 4. Accessibility

- Skeleton containers are `aria-hidden` with the query's `role="status"` label preserved where present.
- Toast region is announced by sonner's built-in live regions.
- `MotionConfig reducedMotion="user"` stays global; `tw-animate-css` dialog animations are not disabled.
- Keyboard: slot buttons remain focusable in DOM order; grouping headers are plain `p` headings (`role=group` not required).

### 5. Verification

`npm run lint`, `npm run typecheck`, `npm run build`; browser checks (existing audit harness) covering: typing filters without submit, skeletons → data, toast on each dashboard mutation, failed mutation rollback (kill backend mid-test or force a 409), slot grouping + selection + stale-clear + sticky summary, reduced-motion rendering. Backend tests unaffected.

## Risks / trade-offs

- **Optimistic updates vs correctness:** rollback + refetch on error keeps the server authoritative; races are handled by React Query's mutation serialization per key. Complexity is confined to list mutations.
- **sonner bundle cost:** ~10kB gz; acceptable, single Toaster, no window.lib.
- **Shadcn copy-in drift:** generated components may assume tokens we don't define; each file is checked against our `globals.css` tokens (border/muted/ring/card) and adjusted, not vendored blindly.
- **Motion jank on long lists:** stagger capped (see §2) so >20-item lists don't cascade.

## Open questions

- None blocking. Default: toasts in English-only, matching current UI copy.
