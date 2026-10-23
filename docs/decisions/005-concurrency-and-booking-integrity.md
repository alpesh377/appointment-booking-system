# 005 — Concurrency and Booking Integrity

| | |
|---|---|
| **Decision ID** | D-005 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.D (prevent overlapping bookings and unavailable slots), 3.E (reschedule and status changes), 3.F / 3.G (dashboards reflecting true state) |
| **Scope additions** | `[P]` per-provider advisory lock, lazy expiry sweep, lock timeout, snapshot columns |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

Two customers can read the same free slot at the same instant. A check-then-insert in application code is a time-of-check/time-of-use race, and the failure is invisible until two bookings exist on one slot:

```
 t0   A: GET slots   -> 09:00 free
 t1   B: GET slots   -> 09:00 free
 t2   A: POST book   -> 201
 t3   B: POST book   -> 201   <-- both hold 09:00
```

Three further concurrency surfaces exist once the lifecycle from D-004 is in place:

- lazy expiry changing a `PENDING` to `EXPIRED` while a booking is being validated,
- reschedule releasing one slot and claiming another in one logical operation,
- cancellation or rejection freeing a slot that a concurrent booking is examining.

Also at stake: correctness must survive a future code path that forgets the application rule. The database therefore has to be the final authority, not the only one.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-BOOK-6 | No overlapping active appointments |
| R-BOOK-7 | No bookings on unavailable slots |
| R-APPT-2 / 3 | Cancel and reschedule must be atomic in effect |
| A3 (D-004) / R-BOOK-6 | Lazy expiry must interact correctly with booking |

---

## 3. Options considered

| Option | Mechanism | Why not chosen |
|---|---|---|
| App-level check | `SELECT` then `INSERT` | Races under concurrency; the classic bug |
| Unique index | `UNIQUE(provider_id, starts_at)` | Fails when durations differ or two services share a start |
| Row lock on provider | `SELECT ... FOR UPDATE` on `provider_profiles` | Works, but overloads a business row with locking semantics and gives no ordering discipline |
| Serialisable isolation everywhere | `SERIALIZABLE` transactions | Correct but requires retry loops throughout; harder to reason about |
| Advisory transaction lock + exclusion constraint | Per-provider `pg_advisory_xact_lock`, `EXCLUDE USING gist` | **Selected**: explicit ordering, no retries, and a database guarantee |
| Cron-based expiry | Scheduled worker | Rejected: no scheduler in scope |

---

## 4. Selected approach

### 4.1 The canonical mutation protocol

Every path that inserts or updates an appointment executes these steps, in this order:

```
BEGIN
  1  pg_advisory_xact_lock(provider_id)          -- always first; no other lock held
  2  sweep_expired(provider_id)                  -- PENDING -> EXPIRED where deadline passed
  3  SELECT target rows FOR UPDATE               -- ordered by appointments.id ASC
  4  CONFIRM preconditions against committed state
       - status still eligible for this transition
       - actor role and ownership
       - cutoff, notice and horizon rules
       - target slot still free (for inserts and moves)
  5  apply mutations (status changes and/or new row)
  6  append appointment_events rows
COMMIT
```

Step 4 is mandatory and is the reason the protocol exists: **preconditions are re-checked after the lock is held**, never trusted from an earlier read or from the request body.

### 4.2 Uniform application

| Path | Lock | Sweep | Rows re-read `FOR UPDATE` | Notes |
|---|---|---|---|---|
| Create booking | provider | yes | none (new row) | sweep releases deadlines before validation |
| Reschedule | provider | yes | original row | original set `RESCHEDULED` **before** inserting successor |
| Customer cancel | provider | yes | target row | cutoff re-confirmed under lock |
| Provider confirm | provider | yes | target row | `PENDING` only |
| Provider reject | provider | yes | target row | `PENDING` only |
| Provider complete | provider | yes | target row | `now >= ends_at` confirmed under lock |
| Admin cancel | provider | yes | target row | `PENDING` / `CONFIRMED` only |
| Availability read | provider, sweep-only transaction committed before the read | yes | — | read performs no writes and holds no lock |

### 4.3 The invariant

> No `INSERT`, `UPDATE` or `DELETE` on `appointments` may execute outside step 1's lock.

This is asserted in code review and exercised by tests, not treated as a convention.

### 4.4 Lazy expiry

```sql
UPDATE appointments
   SET status = 'EXPIRED'
 WHERE provider_id = :provider_id
   AND status = 'PENDING'
   AND hold_expires_at <= now()
RETURNING id;
```

The returned ids are used to append one `appointment_events` row each with `actor_role = 'system'`.

`now()` is not immutable, so a partial exclusion-constraint predicate cannot express the deadline. Expiry must therefore be **materialised into the status** before an insert is validated — which is exactly what step 2 does.

### 4.5 The database safeguard

```sql
ALTER TABLE appointments
  ADD CONSTRAINT appointments_no_overlap
  EXCLUDE USING gist (
    provider_id WITH =,
    tstzrange(starts_at, ends_at) WITH &&
  )
  WHERE (status IN ('PENDING', 'CONFIRMED'));
```

Requires the `btree_gist` extension, created in the first Alembic migration.

Because the predicate is status-only, a terminal transition automatically frees the slot, and a reschedule frees the original at the moment it becomes `RESCHEDULED`.

A `23P01` violation maps to `409 SLOT_UNAVAILABLE` and aborts the transaction.

### 4.6 Reschedule ordering

Update-then-insert is not stylistic:

1. Setting the original to `RESCHEDULED` removes it from the constraint predicate.
2. The successor insert is then evaluated against the remaining active rows only.
3. Inserting first would collide with the row about to be retired.

### 4.7 Lock ordering and deadlock avoidance

1. Advisory lock **before** any row lock. Never the reverse.
2. Row locks in ascending `appointments.id`.
3. Operations are single-provider by design — D-004 forbids changing provider on reschedule. If a future operation spans providers, acquire provider advisory locks in ascending `provider_id`, and never acquire a second while holding a higher one.
4. `lock_timeout` is set to 5 seconds `[P]` (A11), so contention fails fast as `409` instead of hanging a request.
5. The advisory lock is transaction-scoped and released automatically on commit or rollback. There is no manual release path and therefore no leak on error.

### 4.8 Snapshots

`appointments.starts_at`, `ends_at` and `duration_minutes` are written once at booking and never recomputed from live service configuration. Without this, editing a service duration would retroactively move past appointments and could violate the overlap constraint.

---

## 5. Reasons

- The exclusion constraint expresses the actual business rule — one provider cannot hold two live appointments over the same instant — and remains true regardless of application code.
- The advisory lock makes execution order deterministic and cheap, and removes reschedule deadlocks and status-change interleaving without retry loops.
- Sweeping inside the same transaction as the mutation means a released slot is visible to the very request that triggered the sweep.
- Update-then-insert on reschedule is the only ordering that keeps the transaction atomic with respect to the constraint.

---

## 6. Advantages and disadvantages

### Advantages

- Double booking is structurally impossible, not merely unlikely.
- No retry loops, no serialisation-failure handling.
- Reschedule is all-or-nothing; a lost race leaves the original intact.
- Expiry needs no scheduler and takes effect exactly when someone looks.
- The protocol is one sequence, which makes it reviewable and testable.

### Disadvantages

- Requires real PostgreSQL with `btree_gist`; SQLite cannot run these tests.
- Mutations for one provider serialise. Irrelevant at assignment scale, but a hot provider would become a bottleneck.
- The sweep writes during reads (in its own short transaction), which is a maintenance write on a read path and must be documented.
- A forgotten lock in a future endpoint is a silent regression, mitigated only by the constraint and by tests that assert the invariant.

---

## 7. Implications

**Security.** The lock is per provider, so one provider's traffic cannot delay another's. Ownership checks occur inside the lock, after re-reading, which prevents a stale-authorization window.

**Data integrity.** Two independent guards: advisory lock for ordering, exclusion constraint for truth. Foreign keys use restrictive deletes. Snapshot columns make history immutable.

**Performance.** Advisory locks are cheap and held for the duration of one short transaction. Availability reads hold no lock beyond the sweep. Indexes: `(provider_id, starts_at)`, `(customer_id, starts_at)`, `(status, starts_at)`, plus the GiST index backing the constraint.

**Testing.** D-008 requires: two parallel bookings producing exactly one `201` and one `409`; a concurrent reschedule swap; an expiry racing a booking; per-path protocol coverage; and a duplicate-submission case.

---

## 8. Consequences for architecture and future changes

- Repositories own transaction boundaries and lock acquisition; services never open transactions implicitly.
- Any new appointment-mutating endpoint must adopt the protocol. The constraint will still prevent double booking if it does not.
- `btree_gist` must be enabled before the constraint is created in Alembic.
- If contention ever matters, the advisory lock can be narrowed to `(provider_id, date)` without changing the constraint or the API.
- If multi-provider operations appear, the ascending-`provider_id` rule already anticipates them.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| Application-level check-then-insert | Races; the entire problem this decision exists to solve |
| `UNIQUE(provider_id, starts_at)` | Breaks with variable durations and multiple services |
| `SELECT ... FOR UPDATE` on the provider row | Couples locking semantics to a business table and gives no ordering rule |
| `SERIALIZABLE` isolation with retries | Correct but forces retry logic into every caller and obscures failure modes |
| Cron or worker for expiry | Out of scope; needs an always-on process |
| Partial predicate including `now()` | Not immutable; PostgreSQL rejects it |
| Insert-before-update on reschedule | Collides with the row being retired |
| Manual advisory unlock | Leak risk on error paths; transaction scope is safer |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` Per-provider advisory lock, transaction-scoped | Accepted |
| `[P]` Lazy expiry inside the mutation transaction | Accepted |
| `[P]` Lock timeout 5 seconds then `409` (A11) | Accepted |
| `[P]` Snapshot `starts_at`, `ends_at`, `duration_minutes` | Accepted |
| PostgreSQL required for all integration tests | Accepted (D-008) |
| Sweep-on-read accepted as a maintenance write on a read path | Documented limitation |
