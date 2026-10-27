# Tasks

## 1. Foundation and environment

- [x] 1.1 Create the `backend/` and `frontend/` top-level structure with the module boundaries from `design.md` (api, core, models, schemas, services, repositories, tests); verify the tree contains every directory named in the design.
- [x] 1.2 Add backend dependencies and a minimal FastAPI application; verify `GET /health` returns 200 from a local run.
- [x] 1.3 Scaffold the Next.js App Router project with TypeScript, Tailwind CSS, shadcn/ui and TanStack Query; verify the development server renders a placeholder page.
- [x] 1.4 Add local PostgreSQL orchestration and confirm `btree_gist` and `citext` can be created; verify `CREATE EXTENSION` succeeds against the running database.
- [x] 1.5 Create `.env.example` covering database URL, application origin, JWT signing secret, cookie settings and admin seed credentials; verify the backend starts using only a copied example file.
- [x] 1.6 Write the README setup section (prerequisites, environment, database, backend, frontend); verify the documented commands work from a clean checkout.

## 2. Schema and migrations

- [x] 2.1 Initialise Alembic and write a first migration that enables `btree_gist` and `citext`; verify `alembic upgrade head` succeeds on an empty database.
- [x] 2.2 Implement `users` and `provider_profiles` models with the unique case-insensitive email and one-profile-per-provider constraints; verify constraint tests reject duplicates.
- [x] 2.3 Implement `services`, `availability_rules`, `schedule_breaks`, `date_overrides` and `date_override_windows` with their checks and the one-override-per-date uniqueness; verify constraint tests pass.
- [x] 2.4 Implement `appointments` and `appointment_events` with the status check, foreign keys, self-referencing reschedule links and dashboard indexes; verify the migration applies and the indexes exist.
- [x] 2.5 Add the exclusion constraint over `(provider_id, tstzrange(starts_at, ends_at))` for Pending and Confirmed; verify an overlapping insert is rejected with SQLSTATE `23P01`.
- [x] 2.6 Verify migration reversibility with `alembic downgrade base` followed by `alembic upgrade head` on an empty database.
- [x] 2.7 Implement the administrator setup command; verify it creates exactly one active administrator, is safe to run twice, and exits with a clear error when credentials are absent.

## 3. Identity, sessions, authorization and CSRF

- [x] 3.1 Implement password hashing and password-length validation; verify unit tests cover hashing, verification and rejection below eight characters.
- [x] 3.2 Implement registration that always produces a Customer account; verify API tests cover success, duplicate email in mixed case, and an attempted provider role.
- [x] 3.3 Implement sign-in and sign-out using an `HttpOnly` cookie; verify API tests cover valid credentials, invalid credentials with a non-revealing message, sign-out invalidation and refusal of deactivated accounts.
- [x] 3.4 Implement the CSRF dependency: Origin/Referer validation plus a double-submit token in a custom header with constant-time comparison; verify tests cover missing Origin, wrong Origin, missing token, mismatched token, a valid pair and safe-method exemption.
- [x] 3.5 Implement role and ownership authorization dependencies; verify a parametrized matrix over role × endpoint × ownership passes for representative resources.
- [x] 3.6 Implement profile read and update restricted to the authenticated account; verify tests reject cross-account access.
- [x] 3.7 Build the sign-in and registration pages with session-aware navigation; verify signing in, signing out and being redirected from a protected page.
- [x] 3.8 Verify deactivation blocks authenticated actions while preserving appointment history visible to administrators.

## 4. Provider directory

- [x] 4.1 Implement provider profile creation for administrators, including display name, category, optional biography and timezone; verify an API test creates a provider that can then sign in.
- [x] 4.2 Implement the provider listing and search endpoints restricted to active providers, matching name or service category case-insensitively; verify tests cover name match, category match, empty results and hidden deactivated providers.
- [x] 4.3 Implement service create, update and deactivate with duration validation of 15–480 minutes in multiples of 5; verify tests accept a valid duration and reject boundaries and non-multiples.
- [x] 4.4 Implement provider self-service profile updates with ownership enforcement; verify tests allow self-update and reject cross-provider updates.
- [x] 4.5 Implement administrator provider update and deactivation with no cascading deletion; verify existing appointments remain unchanged after deactivation.
- [x] 4.6 Build the provider listing, search and detail pages showing profile and services with durations; verify against seeded data including an empty search result state.
- [x] 4.7 Build provider service management in the provider area; verify creating and deactivating a service changes what the detail page offers.

## 5. Availability and slot engine

- [x] 5.1 Implement the pure slot-generation function covering window composition, weekly and date breaks, closed overrides and open overrides; verify unit tests for each composition rule.
- [x] 5.2 Verify grid behaviour with unit tests for anchoring at window start, duration fitting, refusal to straddle a break and the unused tail at a window end.
- [x] 5.3 Verify horizon and strict notice filtering with boundary tests, including a slot exactly two hours away being excluded.
- [x] 5.4 Verify timezone behaviour with tests for spring-forward and fall-back days, nonexistent and ambiguous local times, and local-midnight day boundaries.
- [x] 5.5 Implement the availability query endpoint for a provider, service and date range, including service-ownership rejection; verify API tests return different slot lists for services of different durations.
- [x] 5.6 Implement provider availability endpoints for working windows, breaks and date overrides, rejecting past dates and overlapping windows; verify API tests cover each rejection.
- [x] 5.7 Implement the query that identifies existing appointments falling outside current availability; verify it excludes appointments merely awaiting completion.
- [x] 5.8 Build the provider availability management page with window, break and date-override editing; verify an edit changes the slots offered on the provider page.
- [x] 5.9 Verify that a provider timezone change warns, affects only future availability and leaves existing appointment instants unchanged.

## 6. Booking and concurrency

- [x] 6.1 Implement the booking service using the per-provider advisory-lock protocol from `design.md`; verify a successful booking creates a Pending appointment and an event row.
- [x] 6.2 Verify the server derives duration from the service and ignores any client-supplied end time; confirm stored start, end and duration remain unchanged after the service duration is edited.
- [x] 6.3 Verify booking validation rejects inactive providers or services, mismatched service ownership, unavailable slots, bookings outside the horizon and bookings inside the notice period.
- [x] 6.4 Implement the lazy expiry sweep with `hold_expires_at = min(created_at + 24h, starts_at − 2h)`; verify tests cover both winning boundaries, slot release and the recorded Expired event.
- [x] 6.5 Verify the exclusion constraint surfaces as `409 SLOT_UNAVAILABLE` and that no partial appointment is persisted.
- [x] 6.6 Verify concurrency tests: two simultaneous bookings yield exactly one success and one conflict, a reschedule swap does not deadlock, an expiry racing a booking resolves correctly, and a duplicate submission creates nothing extra.
- [x] 6.7 Build the booking and confirmation pages including optional notes and the provider timezone label; verify a complete booking flow from provider detail to confirmation.
- [x] 6.8 Verify availability refreshes after a booking so the claimed slot disappears and the confirmation shows the correct status.

## 7. Appointment lifecycle

- [x] 7.1 Implement the transition service with per-transition guards and event appending; verify a table-driven test covers every legal edge and every illegal edge in the lifecycle.
- [x] 7.2 Implement provider confirm and reject, including `409 USE_REJECT` when a provider attempts to cancel a pending request; verify tests for both outcomes.
- [x] 7.3 Implement customer cancellation with the two-hour cutoff; verify tests allow cancellation before the cutoff and refuse it inside the cutoff.
- [x] 7.4 Implement provider cancellation limited to before the end time; verify cancellation after the end time is refused.
- [x] 7.5 Implement completion restricted to the owning provider at or after the end time, with no automatic completion; verify premature completion is refused and a past appointment stays Confirmed without action.
- [x] 7.6 Implement rescheduling as linked successor creation inside one transaction; verify tests cover success, links in both directions, no-op rejection, provider or service change rejection, and full rollback when the new slot is taken.
- [x] 7.7 Verify a rejected successor leaves the original Rescheduled and records both events.
- [x] 7.8 Build the customer dashboard with upcoming, past and cancelled views, date and status filters, detail view and eligibility-gated actions; verify each view against seeded data including empty states.
- [x] 7.9 Build the provider dashboard with today in provider-local time, upcoming, pending requests, and a separate awaiting-completion group; verify today's boundary across a daylight-saving date.
- [x] 7.10 Build the appointment detail view including the event history; verify the displayed transitions match the recorded events for a rescheduled appointment.

## 8. Admin console

- [x] 8.1 Implement the totals and status-distribution endpoints; verify counts include deactivated accounts and match seeded data.
- [x] 8.2 Implement customer listing, deactivation and reactivation; verify deactivation blocks sign-in while appointments remain visible.
- [x] 8.3 Implement the whole-platform appointment list with provider, customer, date and status filters plus pagination; verify combined filters and the reported total.
- [x] 8.4 Implement supervisory cancellation of Pending and Confirmed appointments; verify a cancelled pending request becomes Cancelled rather than Rejected and records an administrator actor.
- [x] 8.5 Verify that administrator attempts to confirm, reject, complete, reschedule, or edit services and availability are all rejected as forbidden.
- [x] 8.6 Implement self-deactivation and last-administrator guards; verify both are refused.
- [x] 8.7 Verify deactivating a provider or customer with future appointments surfaces those appointments and cancels none of them automatically.
- [x] 8.8 Build the admin dashboard, user management and appointment management views; verify totals, filters and the supervisory action from the interface.

## 9. Web experience

- [x] 9.1 Verify every one of the ten required pages renders at mobile and desktop widths without horizontal overflow.
- [x] 9.2 Verify loading indicators appear for delayed responses on each data view using a throttled connection.
- [x] 9.3 Verify explicit empty states for provider search, appointment lists and a date with no slots.
- [x] 9.4 Verify error presentation maps conflict, forbidden and validation responses to messages that name the problem and preserve prior state.
- [x] 9.5 Verify form validation messages identify the offending field for client-side and server-side rejections.
- [x] 9.6 Verify role-appropriate navigation and redirection for unauthenticated visits to protected pages.

## 10. Submission and integration

- [x] 10.1 Complete the README with setup, run, test, environment, API documentation and decision-record links; verify a clean-machine walkthrough reaches a running application.
- [x] 10.2 Verify OpenAPI generation succeeds and `/docs` documents every endpoint, including the CSRF requirement on state-changing operations.
- [x] 10.3 Capture screenshots of the ten required pages; verify the image files exist in the repository.
- [x] 10.4 Verify the full happy path end to end: registration, administrator creates a provider, provider configures hours and a service, customer books, provider confirms, provider completes.
- [x] 10.5 Run the complete backend suite against real PostgreSQL and verify all five mandatory categories plus migration, OpenAPI and seed checks pass.

## 11. Quality and dependency maintenance (post-implementation audit)

- [x] 11.1 Capture the pre-audit baseline: installed versions, existing form/API patterns, test suite, lint and security state.
- [x] 11.2 Adopt React Hook Form + Zod + `@hookform/resolvers` for authentication, registration, profile, service, availability, and administrator forms; keep server-side validation authoritative.
- [x] 11.3 Configure shadcn/ui for Next.js 15 + Tailwind CSS v4 (`components.json`, Radix dialog/alert-dialog/label/slot, `Form` primitives) and integrate the components into existing pages.
- [x] 11.4 Add Motion with reduced-motion handling; keep TanStack Query as the only server-state layer and add no global client store.
- [x] 11.5 Replace the removed `next lint` workflow with an ESLint 9 flat config and add a `typecheck` script.
- [x] 11.6 Split runtime and development dependencies, pin compatible versions, and configure Ruff (lint + format), pytest-cov, Bandit, and pip-audit.
- [x] 11.7 Harden the backend: narrow password verification errors, handle duplicate-email races, allow clearing profile fields, validate availability bodies with the existing schemas, validate status/view filters, and add production configuration guards plus logging.
- [x] 11.8 Improve query efficiency with eager-loaded appointment relations and SQL-level administrator pagination.
- [x] 11.9 Re-run backend tests against PostgreSQL, migrations, coverage, lint, Bandit, and pip-audit; re-run frontend lint, typecheck, build, and browser checks.
- [x] 11.10 Upgrade Tailwind CSS from v3.4 to v4.3 (CSS-first theme, `@tailwindcss/postcss`, `tw-animate-css`, `tailwind-merge` v3) and verify the rendered tokens and responsive layout are unchanged.

## Workflow follow-up

- Archive the change after implementation review is complete.
- Confirm the archived specs match the implemented behaviour before syncing.
