# 004 — Appointment Lifecycle

| | |
|---|---|
| **Decision ID** | D-004 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.D (booking, status display, notes), 3.E (upcoming/past, cancel, reschedule, confirm, reject, complete, details, history), 3.F (customer dashboard lists and eligibility), 3.G (provider pending list and status management) |
| **Scope additions** | `[P]` pending slot hold with lazy expiry, 2-hour cancellation cutoff, provider cancellation, no auto-completion, no `NO_SHOW`, terminal-state immutability, linked-successor reschedule |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The brief names the actions — confirm, reject, cancel, reschedule, complete — but not the rules that govern them. Three gaps mattered most:

1. **Does a pending request reserve its slot?** The brief requires both pending requests and prevention of overlapping bookings. Those interact.
2. **What does "eligible" mean** in "cancel or reschedule eligible appointments"?
3. **Can a reschedule be undone** if the provider rejects the new time?

Without answers, the status set is undefined and the database constraint cannot be written.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-BOOK-5 | Status must be displayed |
| R-BOOK-6 | No overlapping active appointments |
| R-APPT-1 | Upcoming and past views |
| R-APPT-2 / 3 | Customer cancel and reschedule |
| R-APPT-4 / 5 | Provider confirm and reject |
| R-APPT-6 | Provider completes |
| R-APPT-8 | History retained |
| R-CUST-5 | Eligible actions exposed, ineligible ones not |
| R-PROVD-3 / 4 | Pending list and status management |

---

## 3. Options considered

### 3.1 Pending slot reservation

| Option | Rule | Consequence |
|---|---|---|
| A | Pending holds the slot forever | Simple; abandoned requests starve the calendar permanently |
| B | Pending holds the slot until a deadline, released lazily (selected) | Bounded starvation, no scheduler required |
| C | Pending does not hold the slot; competing requests per slot | Most complex; cascading rejections on acceptance |

### 3.2 Cancellation eligibility

| Option | Rule |
|---|---|
| A | Any active appointment until it starts |
| B | Until 2 hours before start, aligned with minimum notice (selected) |
| C | A separate 24-hour policy | 
| D | Provider-configurable cutoff |
| E | Never block, only record lateness |

### 3.3 Reschedule representation

| Option | Shape |
|---|---|
| A | Mutate the existing row, log an event |
| B | Cancel the old row, create a new one with no link |
| C | Linked successor rows (selected) |
| D | Two-phase hold: keep the original until the new time is approved |

---

## 4. Selected approach

### 4.1 Status set

Exactly seven values:

`PENDING` · `CONFIRMED` · `REJECTED` · `CANCELLED` · `COMPLETED` · `EXPIRED` · `RESCHEDULED`

Stored as a `VARCHAR` with a `CHECK` constraint rather than a PostgreSQL enum, so migrations can evolve the list without type surgery.

### 4.2 Pending reservation and expiry

A booking is created as `PENDING` and **holds its slot**. Both a `PENDING` and a `CONFIRMED` appointment participate in the overlap constraint; all other statuses do not.

```
hold_expires_at = min(created_at + 24h, starts_at - 2h)
```

Expiry is applied **lazily**, inside the transaction that reads or writes availability (D-005). There is no scheduler.

A request that is never answered becomes `EXPIRED` and releases its slot. History is preserved; the row is never deleted.

### 4.3 Transitions

```
                     customer books
                           |
                           v
                  +-----------------+  deadline  +-----------+
                  |     PENDING     |----------->|  EXPIRED  |
                  +--------+--------+            +-----------+
                           |
              +------------+-------------+
              |                          |
       provider rejects           provider confirms
              |                          |
              v                          v
        +-----------+              +-----------+
        | REJECTED  |              | CONFIRMED |
        +-----------+              +-----+-----+
                                           |
                +--------------------------+--------------------------+
                |                          |                          |
        now < ends_at              now < ends_at               now >= ends_at
        provider cancels           customer cancels            provider completes
        customer cancels           (before 2h cutoff)                  |
                |                          |                          |
                v                          v                          v
          +-----------+              +-----------+              +-----------+
          | CANCELLED |              | CANCELLED |              | COMPLETED |
          +-----------+              +-----------+              +-----------+
```

Reschedule is a separate branch, described in 4.5.

### 4.4 Transition rules

| From | Action | Actor | Condition | To |
|---|---|---|---|---|
| — | book | customer | slot valid, notice > 2h, within horizon | `PENDING` |
| `PENDING` | confirm | owning provider | — | `CONFIRMED` |
| `PENDING` | reject | owning provider | — | `REJECTED` |
| `PENDING` | cancel | owning customer | before `starts_at − 2h` | `CANCELLED` |
| `PENDING` | cancel | admin | any time | `CANCELLED` |
| `PENDING` | cancel | provider | **forbidden** — `409 USE_REJECT` | — |
| `PENDING` | expire | system (lazy) | `hold_expires_at <= now()` | `EXPIRED` |
| `CONFIRMED` | cancel | owning customer | before `starts_at − 2h` | `CANCELLED` |
| `CONFIRMED` | cancel | owning provider | `now < ends_at` | `CANCELLED` |
| `CONFIRMED` | cancel | admin | any time | `CANCELLED` |
| `CONFIRMED` | complete | owning provider | `now >= ends_at` | `COMPLETED` |
| `PENDING` / `CONFIRMED` | reschedule | owning customer | before `starts_at − 2h` | original → `RESCHEDULED`, successor → `PENDING` |

Terminal states — `REJECTED`, `CANCELLED`, `COMPLETED`, `EXPIRED`, `RESCHEDULED` — accept **no further transitions for any role, including admin**.

### 4.5 Reschedule

Rescheduling **creates a new appointment** linked to the original:

- `original.status = RESCHEDULED`, `original.rescheduled_to_id = successor.id`
- `successor.status = PENDING`, `successor.rescheduled_from_id = original.id`
- the successor inherits customer, provider and service; **only the time changes** `[P]`
- the successor receives the same expiry policy as any new booking
- the original slot is released and the new slot claimed in one transaction (D-005)

Release-then-request consequence: if the provider later rejects the successor, the original **stays** `RESCHEDULED`. The customer has no active appointment and must book again. This is accepted deliberately, not an oversight.

### 4.6 Cancellation metadata

`cancelled_by_role` (`customer` | `provider` | `admin`), `cancelled_by_user_id`, optional `cancellation_reason`.

One `CANCELLED` status serves all three actors. The actor fields carry the distinction; a status per actor was rejected as duplication.

### 4.7 Completion and the no-scheduler rule

- Completion is legal only when `now >= ends_at`, and only by the owning provider.
- There is no automatic completion, no automatic cancellation, no `NO_SHOW` status and no background job.
- A `CONFIRMED` appointment whose end time has passed remains `CONFIRMED` until the provider closes it. Such appointments are surfaced in a dedicated provider dashboard group.
- Consequently, **upcoming vs past is a time predicate** (`ends_at < now()`), not a status predicate.

### 4.8 History

Every transition writes an `appointment_events` row: `from_status`, `to_status`, `actor_user_id`, `actor_role`, `reason`, `created_at`. Reschedule writes two events (original superseded, successor created).

---

## 5. Reasons

- A pending request that holds a slot forever is a calendar leak; a lazy deadline closes it without introducing a scheduler.
- Aligning the cancellation cutoff with the minimum notice yields a clean invariant: **anything a customer could book, they can cancel.** No dead ends in the demo, no surprise errors.
- Linked successor rows preserve the original as a fact rather than as a log entry, satisfying "maintain appointment history" in substance.
- Reusing `CANCELLED` with actor columns keeps filters, statistics and UI branches at seven statuses.
- Making completion depend on `ends_at` gives time itself the role of scheduler, so no process ever has to run in the background.
- Terminal immutability removes an entire class of "undo" paths that would otherwise need their own authorization rules.

---

## 6. Advantages and disadvantages

### Advantages

- No background worker anywhere in the system.
- Every status change has exactly one legal actor and one legal condition.
- The original appointment remains queryable after a reschedule.
- Statistics and dashboards can rely on a small, closed status set.
- Cancellation attribution is complete without extra statuses.

### Disadvantages

- **A rejected reschedule strands the customer.** The original is gone and they must rebook.
- **Stale `CONFIRMED` rows accumulate** if providers do not close out past appointments. The system nudges; it does not force.
- **Pending requests can briefly block a slot** until the 24-hour/2-hour deadline, which a provider must reject to release early.
- **No no-show concept**, so attendance cannot be measured later without a schema change.
- **`409 USE_REJECT`** is a slightly unusual asymmetry: providers must use reject, while admins cancel.

---

## 7. Implications

**Security.** Every transition checks ownership and actor role before state. A customer can never touch another customer's appointment; a provider can never act on another provider's. The `USE_REJECT` rule is enforced server-side, not by hiding a button.

**Data integrity.** The overlap constraint's predicate is exactly `status IN ('PENDING','CONFIRMED')`, so terminal states automatically free their slot. `rescheduled_from_id` / `rescheduled_to_id` are self-referencing foreign keys. Events are append-only.

**Performance.** Status and time indexes (`provider_id, starts_at`), (`customer_id, starts_at`), (`status, starts_at`) keep dashboard queries cheap. Expiry is one indexed `UPDATE` per provider.

**Testing.** Every row of the transition table is a test case, legal and illegal. Additional cases: terminal immutability for all roles, `USE_REJECT`, cutoff boundaries, completion before/after `ends_at`, expiry deadline, reschedule atomicity, and duplicate submission.

---

## 8. Consequences for architecture and future changes

- `appointment_events` is the history mechanism; nothing else records transitions.
- Dashboards must filter by time, not only by status.
- Adding `NO_SHOW` later means a new status, a new transition and a decision about who may set it.
- Adding automatic completion later would require either a scheduler or a lazy write, and would contradict the "completion is an attestation" principle.
- A two-phase reschedule could be introduced later by allowing the predecessor to remain `CONFIRMED` until the successor is approved; the link columns already support it.
- Buffer times could be added without changing the status model.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| No pending expiry | Permanent calendar starvation from abandoned requests |
| Pending does not hold the slot | Requires competing-request queues and cascading rejections |
| Separate `CANCELLED_BY_PROVIDER` / `_CUSTOMER` statuses | Duplicates one state; actor columns carry the same information |
| In-place mutation for reschedule | Original time survives only inside a log payload; weak history |
| Unlinked cancel-and-rebook | Nothing records that the two rows are the same booking |
| Two-phase reschedule holding both slots | One booking occupying two slots complicates the constraint, availability and the provider calendar |
| Auto-completion after `ends_at` | Fabricates an attestation the provider never made |
| `NO_SHOW` status | Adds a transition with no requirement behind it |
| Cancellation allowed up to the start time | Lets a customer strand a slot that nobody else could then book |
| A separate 24-hour cancellation cutoff | Arbitrary, and makes some appointments impossible to cancel in a demo |
| Provider cancelling a pending request | Rejection is the designed response; cancellation would misattribute the outcome |
| Reversible terminal states | Multiplies authorization paths for no required behaviour |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` Pending holds the slot until expiry (A3) | Accepted |
| `[P]` Expiry = `min(+24h, start−2h)`, lazy, no worker | Accepted |
| `[P]` Customer cutoff = `start−2h` (A4) | Accepted |
| `[P]` Provider and admin may override the customer cutoff | Accepted |
| `[P]` Provider cancellation allowed before `ends_at` | Accepted |
| `[P]` Completion only when `now >= ends_at` | Accepted |
| `[P]` No auto-completion, no `NO_SHOW`, no scheduler | Accepted |
| `[P]` Cancellation reason optional (A7) | Accepted |
| `[P]` Reschedule changes time only (A9) | Accepted |
| `[P]` Rejected reschedule does not restore the original (A10) | Accepted |
| `[P]` Terminal states final for all roles | Accepted |
| "Past" boundary for dashboards | U3 — proposed `ends_at < now()` |
