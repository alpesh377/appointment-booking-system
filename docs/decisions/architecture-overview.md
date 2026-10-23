# Architecture Overview

| | |
|---|---|
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Related** | D-002, D-003, D-004, D-005, D-006, D-007, D-010 |

This document explains how the system fits together. It is descriptive: the binding rules live in the decision records and the OpenSpec specification.

---

## 1. System context

```
                        +----------------------------------+
                        |            Browser               |
                        |  Next.js App Router (React)      |
                        |  Server + Client Components      |
                        +----------------+-----------------+
                                         |
                       same-origin fetch | HttpOnly session cookie
                       X-CSRF-Token      | (proxied, not cross-origin)
                                         v
                        +----------------------------------+
                        |         Next.js server           |
                        |  rewrites /api/* -> FastAPI      |
                        |  middleware: UX redirects only   |
                        +----------------+-----------------+
                                         |
                                         v
                        +----------------------------------+
                        |            FastAPI               |
                        |  routers -> services -> repos    |
                        |  authorization + CSRF + slots    |
                        +----------------+-----------------+
                                         |
                                         v
                        +----------------------------------+
                        |          PostgreSQL              |
                        |  btree_gist, citext, exclusion   |
                        |  constraints, timestamptz         |
                        +----------------------------------+
```

Two deployable services, one database. The browser never talks to FastAPI directly, which keeps cookies same-origin and removes CORS credential handling from the critical path.

---

## 2. Responsibilities

### Frontend (Next.js, TypeScript)

| Area | Responsibility |
|---|---|
| Routing | App Router segments for public, customer, provider and admin areas |
| Server Components | Application shell, initial data framing, layout composition |
| Client Components | Forms, filters, slot pickers, optimistic-free interactions |
| Data fetching | TanStack Query for client-side queries and mutations |
| API access | One HTTP wrapper that attaches the CSRF header and handles `401`/`403`/`409` uniformly |
| Authorization (UX) | Hide or disable actions the role cannot perform; redirect unauthenticated users |
| Presentation | Responsive layout, loading, validation, empty and error states |

The frontend never decides authorization. It mirrors it for usability.

### Backend (FastAPI)

| Layer | Responsibility |
|---|---|
| Routers | HTTP surface, request parsing, status codes, OpenAPI metadata |
| Dependencies | Authentication, role checks, ownership checks, CSRF validation |
| Services | Slot generation, appointment lifecycle, rescheduling, admin supervision |
| Repositories | SQLAlchemy queries, transaction boundaries, lock acquisition |
| Models | ORM mappings and Pydantic schemas |

The slot engine is a **pure function**: no I/O, no clock access passed implicitly, no database calls. It receives rules, busy intervals, the candidate dates and "now", and returns slots. This is what makes it directly testable.

### Database (PostgreSQL)

The database is not a passive store. It enforces three invariants the application cannot be trusted to maintain alone:

1. **No overlapping active appointments** — exclusion constraint on `tstzrange`.
2. **No duplicate accounts** — unique, case-insensitive email.
3. **No dangling history** — foreign keys with restrictive deletes; nothing is hard-deleted.

---

## 3. Request flows

### 3.1 Availability lookup

```
Browser            Next.js            FastAPI                  PostgreSQL
   |                  |                  |                         |
   | GET /api/providers/7/availability    |                         |
   |   ?service_id=3&from=...&to=...      |                         |
   |----------------->|                  |                         |
   |                  |----------------->|                         |
   |                  |                  | 1 lock provider (sweep txn)
   |                  |                  | 2 expire stale pendings |
   |                  |                  |------------------------>|
   |                  |                  | 3 load rules, breaks,   |
   |                  |                  |   overrides, busy rows  |
   |                  |                  |<------------------------|
   |                  |                  | 4 slot engine (pure)    |
   |                  |<-----------------| 5 serialize slots       |
   |<-----------------|                  |                         |
```

The sweep runs in its own short transaction under the provider advisory lock and commits before the read. The read itself takes no lock and performs no writes.

### 3.2 Booking

```
POST /api/appointments { provider_id, service_id, starts_at, notes }

  1  authenticate + authorize (customer) + CSRF
  2  BEGIN
  3    pg_advisory_xact_lock(provider_id)
  4    sweep expired pendings for provider
  5    resolve service -> duration (server-side, never from client)
  6    confirm: provider active, service active and owned by provider
  7    confirm: within horizon, notice > 2h, slot inside effective hours,
         outside breaks and overrides, not inside an active appointment
  8    INSERT appointment (PENDING, hold_expires_at, ends_at)
         -- exclusion constraint is the final authority
  9    INSERT appointment_event
 10  COMMIT
 11  201 with appointment details
```

Any `23P01` from step 8 becomes `409 SLOT_UNAVAILABLE` and the transaction rolls back.

### 3.3 Transition (confirm / reject / cancel / complete / reschedule)

All five use the same protocol from D-005: lock, sweep, re-read, confirm, mutate, record, commit. No path mutates an appointment outside that sequence.

---

## 4. Data model

```
users
  id, email (citext, unique), password_hash, role, full_name,
  phone, is_active, created_at, updated_at

provider_profiles
  id, user_id (unique FK), display_name, category, bio,
  timezone (IANA), is_active, created_at, updated_at

services
  id, provider_id FK, name, category, duration_minutes,
  is_active, created_at, updated_at

availability_rules           -- recurring weekly working windows
  id, provider_id FK, weekday (0-6), start_time, end_time

schedule_breaks              -- weekly or date-specific breaks
  id, provider_id FK, weekday NULL, on_date NULL,
  start_time, end_time
  CHECK ((weekday IS NULL) <> (on_date IS NULL))

date_overrides               -- replaces the weekly schedule for one date
  id, provider_id FK, date, is_closed, note
  UNIQUE (provider_id, date)

date_override_windows        -- windows used when is_closed = false
  id, override_id FK, start_time, end_time

appointments
  id, customer_id FK, provider_id FK, service_id FK,
  starts_at (timestamptz), ends_at (timestamptz),
  duration_minutes, status, notes,
  hold_expires_at, rescheduled_from_id, rescheduled_to_id,
  cancelled_by_role, cancelled_by_user_id, cancellation_reason,
  created_at, updated_at

appointment_events
  id, appointment_id FK, from_status, to_status,
  actor_user_id FK, actor_role, reason, created_at
```

### Key constraints

```sql
-- one provider cannot hold two live appointments over the same instant
ALTER TABLE appointments
  ADD CONSTRAINT appointments_no_overlap
  EXCLUDE USING gist (
    provider_id WITH =,
    tstzrange(starts_at, ends_at) WITH &&
  )
  WHERE (status IN ('PENDING', 'CONFIRMED'));
```

| Constraint | Purpose |
|---|---|
| `users.email` unique (citext) | Case-insensitive account uniqueness |
| `provider_profiles.user_id` unique | One provider profile per provider account |
| `date_overrides (provider_id, date)` unique | One override per provider per date |
| `appointments_no_overlap` | The double-booking guarantee |
| Status `CHECK` | Only the seven accepted statuses |
| `service.duration_minutes` `CHECK` | 15–480 and multiple of 5 |

Status is stored as a constrained `VARCHAR` rather than a PostgreSQL enum, so Alembic migrations can evolve it without type surgery.

### Snapshot rule

`starts_at`, `ends_at` and `duration_minutes` are written once at booking and **never recomputed** from current service configuration. Editing a service's duration cannot move a past appointment or break the overlap guarantee.

---

## 5. Slot generation

Inputs: provider timezone, service duration, weekly rules, weekly and date breaks, date overrides, active appointments, `now`.

```
for each date in [from, to]:
    if date outside [today, today + 30 days]: skip
    if a closed override exists for date: skip
    windows = override windows if an override exists
              else weekly rules for that weekday
    breaks  = weekly breaks for weekday + date-specific breaks + busy
    for each window:
        start = window.start            <-- grid anchored at WINDOW start
        while start + duration <= window.end:
            if [start, start + duration] intersects no break and no booking
               and start - now > 2 hours:
                emit start
            start += duration
```

Properties:

- Every emitted slot fits entirely inside effective working time.
- Slots for one service tile without gaps.
- Different services produce different grids; the constraint, not the grid, prevents cross-service overlap.
- Anchoring at the window start keeps the grid stable after cancellations.
- Unused tail at the end of a window is a documented, accepted limitation.

Timezone handling: window bounds are wall-clock local times, resolved per date through `zoneinfo` into instants. DST policy is defined in D-007.

---

## 6. Lifecycle

```
                 customer books
                       |
                       v
              +-----------------+   deadline   +-----------+
              |     PENDING     |------------->|  EXPIRED  |
              +--------+--------+              +-----------+
                       |
        +--------------+---------------+
        |                              |
  provider rejects              provider confirms
        |                              |
        v                              v
  +-----------+                 +-----------+
  | REJECTED  |                 | CONFIRMED |
  +-----------+                 +-----+-----+
                                      |
              +-----------------------+-----------------------+
              |                       |                       |
      now < ends_at           now < ends_at              now >= ends_at
      provider cancels        customer cancels           provider completes
      customer cancels        (before 2h cutoff)                 |
              |                       |                       |
              v                       v                       v
        +-----------+           +-----------+          +-----------+
        | CANCELLED |           | CANCELLED |          | COMPLETED |
        +-----------+           +-----------+          +-----------+

  Reschedule (from PENDING or CONFIRMED, before cutoff):
    original -> RESCHEDULED  ---rescheduled_to--->  successor PENDING
```

Terminal states — `REJECTED`, `CANCELLED`, `COMPLETED`, `EXPIRED`, `RESCHEDULED` — accept no further transitions for any role.

---

## 7. Security architecture

| Concern | Approach |
|---|---|
| Authentication | JWT in an `HttpOnly`, `SameSite=Lax`, `__Host-` prefixed cookie in production |
| Authorization | Server-side role × ownership matrix on every endpoint |
| CSRF | Origin validation + double-submit token in a custom header + cookie attributes |
| Password storage | Argon2id |
| Transport | Same-origin proxy; no wildcard CORS |
| Enumeration | Login errors do not reveal whether an email exists |
| Deactivation | Authenticated actions rejected; records preserved |
| Rate limiting | Out of scope (recorded) |

Frontend guards are UX only. Every protected operation is re-checked in FastAPI.

---

## 8. Cross-cutting conventions

| Topic | Convention |
|---|---|
| Errors | Stable machine-readable `code` plus human `message`; `409` for state conflicts, `403` for authorization, `422` for validation |
| Validation | Pydantic schemas at the edge; domain rules in services; database constraints as the last line |
| Pagination | Server-side, 20 per page (U4) |
| Ordering | Appointments by `starts_at`; lists newest-first where chronological order is meaningless |
| Logging | Structured request logs; no secrets, tokens or password material |
| Time | UTC in the database, provider-local in presentation |
| IDs | Integer primary keys for readability in a demo context |

---

## 9. Proposed directory layout

```
backend/
  app/
    api/            routers grouped by role and resource
    core/           config, security, csrf, errors, logging
    models/         SQLAlchemy models
    schemas/        Pydantic request/response models
    services/       availability, booking, lifecycle, admin
    repositories/   query and transaction helpers
  alembic/          migrations
  tests/            unit, integration, concurrency
frontend/
  app/              routes grouped by role
  components/       shared UI and shadcn primitives
  lib/              api client, auth helpers, formatting
  hooks/            TanStack Query hooks
docs/decisions/     this folder
```

Names may shift during implementation; the boundaries between routers, services, repositories and models are the durable part.

---

## 10. What this architecture deliberately does not do

- No background worker, queue or scheduler.
- No event bus or eventual consistency.
- No cross-service transactions beyond a single PostgreSQL database.
- No client-side authorization.
- No shared ORM between frontend and backend.

Each omission is a decision recorded elsewhere, not an oversight.
