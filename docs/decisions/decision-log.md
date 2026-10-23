# Decision Log

| | |
|---|---|
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Purpose** | One-glance, searchable summary. Detail lives in the individual records. |

All decisions below were accepted together as the v2 consolidated baseline. Detail, alternatives and trade-offs are in the linked record.

---

## Decisions

| ID | Decision | Status | Date | Requirements | Scope |
|---|---|---|---|---|---|
| D-001 | One account, one role. Public registration creates Customers only; admins create provider accounts; first admin via documented seed command; deactivation is soft. | Accepted | 2026-10-23 | `[R]` 3.A, 3.B, 3.H | `[P]` seed command, single-role accounts |
| D-002 | Providers offer 1..N services; each service carries name, category and duration. No provider-level duration. Durations 15–480 min in steps of 5. No pricing. | Accepted | 2026-10-23 | `[R]` 3.B, 3.D | `[P]` duration bounds |
| D-003 | Availability = weekly windows + weekly/date breaks + replacing date overrides. Slots anchored at window start, step equals service duration, must fit entirely in free time. 30-day horizon, strict 2h notice. Edits are prospective only. | Accepted | 2026-10-23 | `[R]` 3.B, 3.C, 3.D | `[P]` horizon, notice, grid anchoring, prospective edits, today-onward validation |
| D-004 | Seven statuses. Pending holds its slot and expires lazily. Linked-successor reschedule. Completion only after `ends_at`; provider cancel only before it. Terminal states absolute. Every transition recorded in `appointment_events`. | Accepted | 2026-10-23 | `[R]` 3.D, 3.E, 3.F, 3.G | `[P]` expiry, cutoff, provider cancel, no auto-completion, no `NO_SHOW` |
| D-005 | Per-provider `pg_advisory_xact_lock` protocol applied uniformly, with in-transaction confirmation, plus a PostgreSQL exclusion constraint as the final overlap safeguard. Lazy expiry sweep. Snapshotted appointment times. | Accepted | 2026-10-23 | `[R]` 3.D, 3.E | `[P]` advisory lock, lazy sweep, lock timeout |
| D-006 | FastAPI is the sole authorization authority. JWT in an `HttpOnly` `SameSite=Lax` cookie over a same-origin Next.js proxy. CSRF defense = Origin validation + double-submit token + custom header + cookie attributes. | Accepted | 2026-10-23 | `[R]` 3.A, 5 | `[T]` cookie transport, CSRF mechanism |
| D-007 | Per-provider IANA timezone; availability generated in provider-local wall clock; instants stored as `timestamptz`; display in provider timezone with label. `zoneinfo`; local-midnight day boundaries; documented DST policy. | Accepted | 2026-10-23 | `[R]` 3.C, 3.D | `[P]` timezone model, DST policy |
| D-008 | Five mandatory backend test categories plus migration, OpenAPI and seed checks. Real PostgreSQL only. One Playwright path optional. | Accepted | 2026-10-23 | `[R]` 5, 6 (quality) | `[P]` test scope |
| D-009 | Admin may cancel any active appointment, and manage accounts within stated boundaries. No confirm/reject/complete/reschedule on behalf, no role changes, no hard deletes. | Accepted | 2026-10-23 | `[R]` 3.H | `[P]` supervision boundaries |
| D-010 | Next.js App Router + TypeScript + Tailwind + shadcn/ui + TanStack Query + Server Components; FastAPI + Pydantic + SQLAlchemy 2.0 + Alembic; PostgreSQL with `btree_gist`. | Accepted | 2026-10-23 | `[R]` 5 | `[T]` stack |

---

## Business-rule assumptions

| ID | Assumption | Value | Record |
|---|---|---|---|
| A1 | Minimum booking notice | `starts_at − now > 2h`, strict | D-003 |
| A2 | Booking horizon | 30 days | D-003 |
| A3 | Pending expiry | `min(created_at + 24h, starts_at − 2h)` | D-004 |
| A4 | Customer cancel/reschedule cutoff | `starts_at − 2h` | D-004 |
| A5 | Service duration bounds | 15–480 min, multiples of 5 | D-002 |
| A6 | DST policy | skip nonexistent, first occurrence ambiguous | D-007 |
| A7 | Cancellation reason | optional | D-004 |
| A8 | Schedule edit window | today and future | D-003 |
| A9 | Reschedule scope | time only | D-004 |
| A10 | Rejected reschedule | does not restore original | D-004 |
| A11 | Advisory lock timeout | 5 seconds | D-005 |

---

## Rejected at scope level

| Rejected | Reason | Record |
|---|---|---|
| Payments / pricing | Not required | requirements-and-scope |
| Email notifications | Not required; external dependency | requirements-and-scope |
| Provider self-registration | Conflicts with admin-managed providers | D-001 |
| Multi-role accounts | Complicates every authorization check | D-001 |
| `NO_SHOW` status | Adds a transition with no requirement behind it | D-004 |
| Automatic completion | Fabricates an attestation nobody made | D-004 |
| Background scheduler | All time rules are lazy or predicate-based | D-004, D-005 |
| Appointment buffers | Invents an unstated duration | D-003 |
| Fixed-step slot grid | Multiplies test surface, invents granularity | D-003 |
| Blocking availability edits | Couples schedule editing to every booking | D-003 |
| `UNIQUE(provider_id, starts_at)` | Fails with variable durations | D-005 |
| `localStorage` tokens | Exposed to JavaScript | D-006 |
| `SameSite=Lax` as sole CSRF defense | Incomplete coverage | D-006 |
| Customer-timezone display | Large UI surface, no requirement | D-007 |
| SQLite test database | Cannot exercise the exclusion constraint | D-008 |
| Admin full operational parity | Fabricates completions, muddies reschedule ownership | D-009 |

---

## Supersession policy

A decision is never edited silently. To change one:

1. Amend or add a record, and give it a new date.
2. Mark the old record `Superseded` and link to its replacement.
3. State what changed and why.

Terminal statuses in this log: `Proposed` → `Accepted` → `Superseded`.
