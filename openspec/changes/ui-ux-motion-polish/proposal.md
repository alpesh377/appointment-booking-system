# Proposal

## Why

The application has a complete, spec-compliant interface, but the experience around it is minimal: loading views are text prompts instead of layout placeholders, all feedback arrives as inline alerts (including successful saves and deletions), search requires an explicit submit, the booking slot picker is a plain button grid without visual affordance, and the shared `motion` dependency is used for a single entrance fade. A polish pass using the existing shadcn/ui component stack, a toast system, and small motion interactions makes day-to-day flows (browse → book → manage) faster to use and easier to status, without touching any API contract or backend service.

## What Changes

- Add the missing shadcn/ui primitives the flows need (`skeleton`, `toast`/sonner, `empty`, `tabs`, `separator`) and mount the `Toaster` in the root layout.
- Build a small shared motion toolkit (`components/motion.tsx`) on `motion/react`: staggered grid/list entrances, press feedback, animated presence for re-queried lists, and an animated selection indicator — all disabled when the OS requests reduced motion.
- Provider listing: debounced live search (no submit needed), skeleton grid while loading, results count announced via `aria-live`, animated empty states with a call to action, hover lift on provider cards.
- Booking flow: slot picker grouped into Morning/Afternoon/Evening with a sliding selection indicator, animated availability re-query, sticky order-summary card, inline pending state on the submit button, success and error feedback via toast + alert.
- Provider and admin dashboards: per-section skeletons, toast confirmation for every mutation (create/update/delete/confirm/reject/complete/reschedule), and optimistic updates that roll back with an error toast if the request fails.
- Appointment detail: animated status transitions so status changes are visible, plus toasts on cancel/reschedule.
- Accessibility guardrails: motion respects `prefers-reduced-motion`, toast and status-teller regions are announced, and focus-visible styles remain consistent.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `web-experience`: adds requirements for live search behaviour, skeleton placeholders, toast-based operation feedback with optimistic updates, resumable slot selection (grouped slots, sticky summary), and motion behaviour including reduced-motion handling. The existing requirements (pages present, responsive layouts, loading/validation/empty/error reporting, role navigation) remain in force; these additions refine how they present.

## Impact

- **Code:** frontend only — `frontend/src/components/**` (new/extended primitives, motion toolkit), `frontend/src/app/**` (all pages touched for loaders/feedback), `frontend/src/components/providers.tsx` (Toaster mount).
- **Dependencies (frontend only):** `sonner` and `motion` (already present, widened usage); skeleton/empty/tabs/separator/toast come in as shadcn copy-in components.
- **APIs:** none changed — every request/response contract used today is preserved. Optimistic updates are client-side cache edits in React Query and roll back on failure, so no new backend behaviour is implied.
- **Verification:** existing lint/typecheck/build checks plus browser checks of the browse → book → manage flows; backend tests are not affected.
