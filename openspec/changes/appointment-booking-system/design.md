# Design

## Context

See `proposal.md` — Why. This document covers how the behaviour specified in `specs/` is produced.

The repository currently contains no application code: only the approved decision baseline in `docs/decisions/` and this change. The design therefore starts from an empty database and an empty frontend, with no migration of existing data to consider.

Binding constraints:

- Next.js + TypeScript, Python FastAPI, PostgreSQL (assignment §5).
- Accepted decisions D-001 … D-010, including the seven-status lifecycle, the duration-equals-step slot grid, the per-provider concurrency protocol, and the layered CSRF defence.
- No background worker, queue or scheduler anywhere in the system.
- One role per account; no multi-role users.

## Goals / Non-Goals

**Goals:**

- A single coherent request path from browser to database, with one authorization authority.
- A slot-generation function that is pure, deterministic and directly unit-testable.
- Non-overlap enforced by the database rather than by convention, and correct under concurrency.
- A lifecycle with one legal actor and one legal condition per transition.
- A code layout where routers, domain services and persistence are separable and independently testable.

**Non-Goals:**

- Horizontal scale-out, caching layers, or read replicas.
- Multi-tenancy, organisations, or per-tenant isolation.
- Event sourcing beyond the append-only appointment event log.
- Offline support, push notifications, or real-time updates.
- Payments, email delivery, waitlists, or provider self-registration.

## Decisions

### D1 — Same-origin Next.js proxy in front of FastAPI

The browser calls `/api/*` on the Next.js origin; `rewrites` forwards to FastAPI. This removes credentialed CORS and makes `HttpOnly` cookies viable, which in turn removes the need to expose a bearer token to JavaScript.

*Alternatives:* direct cross-origin calls (requires `SameSite=None`, credentialed CORS, preflight handling); NextAuth as identity provider (splits authority across two services).

*Consequence:* `APP_ORIGIN` and the rewrite target become the single integration point to configure and document.

### D2 — Layered backend: routers → services → repositories

- **Routers** own HTTP concerns only: parsing, status codes, OpenAPI metadata.
- **Dependencies** own authentication, role/ownership checks and CSRF validation.
- **Services** own domain rules: slot generation, booking, lifecycle transitions, administration.
- **Repositories** own queries, transaction boundaries and lock acquisition.

*Alternatives:* routers calling the ORM directly (couples HTTP to persistence, makes the slot engine untestable, scatters transaction boundaries).

*Consequence:* every mutating endpoint follows the same shape, and the concurrency protocol cannot be split across layers by accident.

### D3 — Slot generation as a pure function

Signature in spirit:

```
generate_slots(
    provider_timezone, service_duration,
    weekly_windows, weekly_breaks, date_breaks,
    date_override_or_none, busy_intervals,
    date_from, date_to, now,
) -> list[instant]
```

No database session, no ambient clock, no configuration lookup. The caller loads data and passes it in.

*Why:* the highest rule density in the system sits in one function; making it pure is what allows the five mandatory test categories to exist at all.

*Alternative:* a service that queries inside the loop — untestable without a database and prone to N+1 queries.

### D4 — Grid anchored at window start, step equal to duration

For each effective window, candidates begin at the window start and advance by the service duration. A candidate is emitted only if the whole interval fits inside free time after breaks and active appointments.

*Alternatives:* fixed 15/30-minute step (better utilisation, larger slot lists, overlapping candidate grids); provider-configurable step (extra setting and variance).

*Consequence:* up to `duration − 1` minutes at the end of a window may be unusable. Accepted and documented.

### D5 — Availability composition order

1. Closed override → no windows.
2. Open override → its windows replace the weekday's windows.
3. Otherwise → the weekday's windows.
4. Subtract weekly breaks, date breaks and active appointments.
5. Apply the grid.
6. Filter by horizon and strict notice.

There are no stored slot rows: availability is always derived, so it cannot go stale.

### D6 — Timezone resolution

Working times are `time` values interpreted in the provider's IANA zone. For each date, window bounds are resolved to instants with `zoneinfo`. Local-day boundaries are computed by resolving local midnight, never by adding 24 hours.

DST policy: skip nonexistent local times; take the first occurrence of ambiguous ones (`fold=0`).

*Consequence:* the overlap constraint operates on `tstzrange` and is therefore timezone-independent.

### D7 — Per-provider advisory lock plus exclusion constraint

Every appointment mutation runs:

```
BEGIN
  pg_advisory_xact_lock(provider_id)
  sweep expired pendings for the provider
  SELECT affected rows FOR UPDATE (ascending id)
  confirm preconditions against committed state
  mutate and/or insert
  append appointment events
COMMIT
```

The database additionally enforces:

```sql
EXCLUDE USING gist (provider_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
  WHERE status IN ('PENDING','CONFIRMED')
```

*Alternatives:* application check-then-insert (races); unique index on start time (fails with variable durations); `SERIALIZABLE` with retries (correct but forces retry logic everywhere).

*Consequence:* `btree_gist` must exist before the constraint; `lock_timeout` is set so contention fails as `409` rather than hanging.

### D8 — Event-sourced status history, not event-sourced state

`appointments` holds current state. `appointment_events` is an append-only log of transitions. This satisfies "maintain appointment history" without introducing projections or replay.

*Alternative:* reconstructing status from events — more machinery for no requirement.

### D9 — Snapshot appointment intervals

`starts_at`, `ends_at` and `duration_minutes` are written once at booking. They are never recomputed from `services`.

*Why:* otherwise changing a service duration would retroactively move history and could violate the overlap constraint.

### D10 — Session and CSRF

- JWT in an `HttpOnly`, `SameSite=Lax`, `__Host-`-prefixed cookie in production.
- FastAPI issues and verifies the token; Next middleware only redirects.
- CSRF: Origin/Referer validation, double-submit token in a non-`HttpOnly` cookie echoed via `X-CSRF-Token`, constant-time comparison, cookie attributes as defence in depth.
- Token regenerated on sign-in and sign-out.

*Alternatives:* `localStorage` tokens (XSS exposure); `SameSite` alone (incomplete); stateful session store (extra storage with no requirement).

### D11 — Error contract

| Situation | Status | Code |
|---|---|---|
| Validation failure | 422 | field-specific |
| Unauthenticated | 401 | `UNAUTHENTICATED` |
| Wrong role or ownership | 403 | `FORBIDDEN` |
| CSRF failure | 403 | `CSRF_ORIGIN_MISMATCH` / `CSRF_TOKEN_INVALID` |
| Slot conflict | 409 | `SLOT_UNAVAILABLE` |
| Illegal transition | 409 | `INVALID_TRANSITION` |
| Provider cancels a pending request | 409 | `USE_REJECT` |
| Passed cutoff | 403 | `CUTOFF_PASSED` |
| Duplicate email | 409 | `EMAIL_TAKEN` |

The frontend maps these codes to messages through one HTTP wrapper, so error presentation cannot diverge between pages.

### D12 — Frontend data flow

- Server Components render the shell, navigation and role-appropriate layout.
- TanStack Query owns client-side fetching, caching and mutation invalidation.
- One query-key convention per resource so a mutation invalidates exactly the affected lists (for example, a booking invalidates availability and both dashboards).

*Trade-off:* mixing ad-hoc `fetch` with TanStack Query would fragment loading and error handling, so all client data access goes through the query layer.

### D13 — Testing shape

- Slot engine: pure unit tests, no database.
- Integration and concurrency: real PostgreSQL, transactional rollback per test except where commits are required.
- Authorization matrix: parametrized over role × endpoint × ownership.
- Lifecycle: table-driven over the transition matrix, legal and illegal.
- Reschedule atomicity: conflict injection inside the transaction.

*Non-goal:* coverage percentages and load testing.

## Data model

```
users(id, email citext unique, password_hash, role, full_name, phone,
      is_active, created_at, updated_at)

provider_profiles(id, user_id unique FK, display_name, category, bio,
                  timezone, is_active, created_at, updated_at)

services(id, provider_id FK, name, category, duration_minutes,
         is_active, created_at, updated_at)

availability_rules(id, provider_id FK, weekday, start_time, end_time)
schedule_breaks(id, provider_id FK, weekday NULL, on_date NULL, start_time, end_time)
date_overrides(id, provider_id FK, date, is_closed, note)   -- unique per provider+date
date_override_windows(id, override_id FK, start_time, end_time)

appointments(id, customer_id FK, provider_id FK, service_id FK,
             starts_at timestamptz, ends_at timestamptz, duration_minutes,
             status, notes, hold_expires_at,
             rescheduled_from_id, rescheduled_to_id,
             cancelled_by_role, cancelled_by_user_id, cancellation_reason,
             created_at, updated_at)

appointment_events(id, appointment_id FK, from_status, to_status,
                   actor_user_id FK, actor_role, reason, created_at)
```

Status is stored as a constrained `VARCHAR` rather than a native enum, so Alembic can add values without type surgery.

## Risks / Trade-offs

- **Unused grid tail** → documented in D-003; acceptable because durations are provider-chosen and the alternative multiplies test surface.
- **Stale `CONFIRMED` appointments** → time-based bucketing in queries plus an explicit awaiting-completion group; no automatic transition.
- **Rejected reschedule strands the customer** → accepted consequence of release-then-request; the UI must make the outcome explicit when a successor is rejected.
- **Sweep-on-read writes during a read path** → the sweep runs in its own short transaction under the provider lock and commits before the read; documented rather than hidden.
- **Per-provider serialisation** → acceptable at assignment scale; the lock could later narrow to `(provider_id, date)`.
- **Proxy misconfiguration breaks auth** → `APP_ORIGIN` and the rewrite target are the only integration variables, both validated at startup and documented in the README.
- **DST day boundaries** → dedicated tests; local midnight resolution is used everywhere a "day" is needed.
- **Service rename affects historical display** → the service name is not snapshotted; recorded as a known limitation in D-002.
- **Too many slots on long horizons** → the 30-day horizon bounds the response; pagination is not needed for slots.

## Migration Plan

1. Initial Alembic migration creates `btree_gist` and `citext`, then the full schema, indexes and the exclusion constraint.
2. A second migration or the same revision seeds nothing; reference data is created only by the setup command.
3. The setup command creates the first Administrator from environment-supplied credentials and is idempotent with respect to an existing administrator.
4. Rollback is `alembic downgrade base`, which drops the schema; acceptable because no production data exists.
5. Order of deployment locally: PostgreSQL → migrations → backend → frontend.

## Open Questions

Deferrable; none changes the specs or the task breakdown.

- **U1** Session lifetime and refresh strategy — proposed: short-lived token, re-login on expiry, no refresh tokens.
- **U2** Service category taxonomy — proposed: free text with suggestions.
- **U4** Page size — proposed: 20 per page.
- **U5** Local topology — proposed: `docker-compose` for PostgreSQL plus both services.
- **U7** Seed data volume — proposed: small curated fixture set.
- **U9** Screenshots — proposed: manual capture during the final run.
