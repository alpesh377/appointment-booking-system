# Tasks

## 1. Primitives and motion toolkit

- [x] 1.1 Add shadcn primitives (`skeleton`, `sonner`/`toast`, `empty`, `tabs`, `separator`), adjust each to our Tailwind v4 tokens, and verify `npm run typecheck`.
- [ ] 1.2 Mount the themed `Toaster` in `src/app/layout.tsx` with `toastSuccess`/`toastError` wrappers; verify a manually fired toast renders and dismisses in the browser.
- [ ] 1.3 Extend `components/motion.tsx` with `StaggerGroup`/`StaggerItem`, `Pressable`, `Swap`, `SelectionHighlight`, and `StatusBadge`, all no-ops under reduced motion; verify each renders in isolation and animations skip with the OS preference set (browser check).

## 2. Provider listing

- [ ] 2.1 Debounced live search without submit and a results-count line announced via `aria-live`; verify typing filters the grid and clearing restores everything (browser check).
- [ ] 2.2 Skeleton card grid during load, `Swap` around the grid, and `Empty` states with a browse CTA; verify skeletons appear then data replaces them, and each empty state renders with its action (browser check).
- [ ] 2.3 `Pressable` + staggered entrance + hover lift on provider cards; verify cards animate on entry and press without layout shift (browser check).

## 3. Booking flow

- [ ] 3.1 Group the slot grid by part of the day with `SelectionHighlight` selection and `Swap` re-query animation; verify grouping, selection persistence, and re-query fade (browser check).
- [ ] 3.2 Add the sticky booking summary (provider, service, duration, date, time) beside the submit action; verify the summary updates with each choice and that changing service or date clears a stale slot (browser check).
- [ ] 3.3 Inline pending state on the submit button plus toast + alert feedback for success and failure; verify a successful booking toasts then redirects, and a failed booking toasts the error while keeping the alert (browser check).

## 4. Dashboards and appointment detail

- [ ] 4.1 Provider dashboard (appointments, services, availability): skeleton sections per query and toasts on every mutation; verify each save/delete shows a confirmation and loaders show skeletons (browser check).
- [ ] 4.2 Optimistic updates with rollback for provider appointment mutations; verify an intentional failure restores the prior list and shows an error toast without leaving a stale row (browser check with backend rejected).
- [ ] 4.3 Admin console (dashboard, users, appointments): skeletons, toasts, optimistic row updates for deactivate/reactivate and cancel; verify add/remove/update reflect instantly and role restrictions are unaffected (browser check).
- [ ] 4.4 Appointment detail: `StatusBadge` transitions plus cancel/reschedule feedback; verify a status change animates and actions toast (browser check).

## 5. System verification

- [ ] 5.1 Run `npm run lint`, `npm run typecheck`, `npm run build` until all pass; record results in the task notes.
- [ ] 5.2 Run reduced-motion and keyboard-only passes over listing → booking → dashboards; verify every control is operable with animations disabled and via keyboard (browser checks).

## Workflow follow-up

- Optional: after implementation is complete and reviewed, archive this OpenSpec change (`/openspec-archive-change`).
