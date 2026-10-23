# 009 — Admin Supervisory Powers

| | |
|---|---|
| **Decision ID** | D-009 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.H (totals, customer accounts, provider create/update/deactivate, all appointments, filtering, statistics), 3.A (role-based access) |
| **Scope additions** | `[P]` supervisory cancellation only; account-management boundaries; no role changes; last-admin guard |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The brief is specific about provider management and vague about appointment management:

```
  SPECIFIC                                            VAGUE
  +----------------------------------------+   +-----------------------------------+
  | Create, update, deactivate providers   |   | "View and manage customer accounts"|
  | View all appointments                  |   | "View and manage ... appointments" |
  | Filter by provider/customer/date/status|   |                                   |
  | Overall statistics                     |   |  manage = ?                       |
  +----------------------------------------+   +-----------------------------------+
```

"View" is unambiguous. "Manage" could mean read-only, emergency cancellation, or full operational parity. The choice affects the integrity of every statistic and the meaning of every audit record.

Two constraints were already fixed: terminal appointment states are final for everyone (D-004), and deactivation never deletes history (D-001). So any admin power operates only on `PENDING` and `CONFIRMED`.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-ADMIN-1 | Totals must be trustworthy |
| R-ADMIN-2 | Customer accounts viewed and deactivated |
| R-ADMIN-3 | Provider accounts created, updated, deactivated |
| R-ADMIN-4 | All appointments visible |
| R-ADMIN-5 | Filters by provider, customer, date, status |
| R-ADMIN-6 | Statistics |
| R-AUTH-5 | Role boundaries respected |

---

## 3. Options considered

| Option | Powers | Consequence |
|---|---|---|
| A | Read-only appointments | Leaves confirmed appointments unresolvable when a provider disappears |
| B | **Supervisory cancellation only (selected)** | Covers disputes and abandonment without fabricating completions |
| C | Full operational parity | Admin can confirm, reject, complete, reschedule, cancel |
| D | Parity minus completion | Still misattributes reschedules and confirmations |

---

## 4. Selected approach

### 4.1 Appointment powers

| Action | Admin |
|---|---|
| View and filter all appointments | yes |
| Cancel `PENDING` | yes, any time |
| Cancel `CONFIRMED` | yes, any time |
| Confirm / reject | no |
| Complete | no |
| Reschedule | no |
| Edit availability or services | no |
| Reverse a terminal state | no |

Admin cancellation records `cancelled_by_role = admin`, `cancelled_by_user_id`, an optional reason, and an `appointment_events` row.

Cancelling a `PENDING` appointment produces `CANCELLED`, **not** `REJECTED`. Attributing a rejection to a provider who never saw the request would corrupt the record.

The `409 USE_REJECT` rule from D-004 applies to providers only. An admin may legitimately cancel a pending request to end it immediately rather than waiting for expiry.

### 4.2 Account powers

| Question | Decision |
|---|---|
| Create provider accounts | yes, with an initial password |
| Edit provider accounts | yes — profile fields only (U8) |
| Deactivate provider accounts | yes |
| Edit provider services or availability | no — provider-owned |
| Create customer accounts | no — registration is public |
| Edit customer profiles | no — deactivate only |
| Deactivate customer accounts | yes |
| Change a user's role | no |
| Hard-delete a user, provider or service | no |
| Deactivate own account | no |
| Deactivate the last active admin | no |

### 4.3 Deactivation with future appointments

Deactivating a provider or customer who has future active appointments is **allowed**. Affected appointments are surfaced in an admin group for manual resolution. Nothing is cancelled automatically.

This mirrors D-003's principle for availability: **state changes never cascade; consequences are surfaced and resolved deliberately.**

### 4.4 Reasons

Admin actions prompt for a reason where applicable, but it is never mandatory `[P]` (A7).

---

## 5. Reasons

- Cancellation is the one supervisory action with no substitute. Expiry handles unanswered requests and customers can cancel their own, but a provider who abandons a confirmed appointment leaves a record nobody else can close.
- Completion must remain an attestation. An admin marking `COMPLETED` asserts a service was delivered, which is the same fabrication D-004 rejected for automatic completion.
- Reschedule-on-behalf has no clean owner: the successor is a request the provider must approve, and the admin would be choosing a time for someone else.
- Keeping operational data provider-owned avoids two writers on the slot engine.
- Refusing role changes preserves the "admin creates providers" model and keeps every authorization check single-valued.
- The last-admin and self-deactivation guards prevent a trivially avoidable system lockout.

---

## 6. Advantages and disadvantages

### Advantages

- Every statistic means what it says: a completion is always a provider's attestation.
- Audit records never attribute an action to someone who did not perform it.
- One extra actor value covers admin cancellation; no new status or mechanism.
- Account deactivation cannot silently destroy someone else's schedule.
- A single consistent principle across availability edits and account deactivation.

### Disadvantages

- If a provider abandons the platform, an admin can only cancel — never complete — so those appointments never enter completed statistics.
- Admins cannot fix a mis-clicked confirmation or rejection on a provider's behalf; the provider must act.
- Manual resolution of affected appointments after deactivation is operational work, not automation.
- The provider/admin cancellation asymmetry (`USE_REJECT`) is a rule reviewers may question.

---

## 7. Implications

**Security.** Admin powers are explicit and narrow. Role checks are per endpoint. Self-deactivation and last-admin guards are server-enforced, not UI-only. Admin cancellation cannot resurrect terminal rows.

**Data integrity.** Statistics distinguish completion from cancellation because only providers can complete. `cancelled_by_role` makes supervisory cancellations auditable without a second status. Deactivation never orphans appointments.

**Performance.** Admin lists are the widest queries in the system; server-side pagination and filters (U4) are required rather than optional.

**Testing.** Authorization matrix must cover admin attempts at confirm/reject/complete/reschedule and expect `403`. Guards for self-deactivation and last-admin need explicit cases. Admin cancellation of `PENDING` must assert `CANCELLED`, not `REJECTED`.

---

## 8. Consequences for architecture and future changes

- Admin appointment views are read-heavy with filters; they do not need the mutation protocol except for cancellation, which uses it in full (D-005).
- A future "admin correction" feature would need its own decision, and would have to explain how it preserves the attestation principle.
- If an admin "complete on behalf" is ever approved, statistics would need a way to distinguish it — a design change, not a flag.
- Provider deactivation affected-appointment surfacing shares its query shape with D-003's availability-conflict group, but the two must remain separate lists.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| Read-only appointments | Leaves confirmed appointments unresolvable; a customer inside the cutoff has no path |
| Full operational parity | Fabricates completions and misattributes confirmations and rejections |
| Parity minus completion | Still lets an admin create a request in the customer's name |
| Separate `CANCELLED_BY_ADMIN` status | Duplicates one state; the actor column carries it |
| Allowing role changes | Bypasses admin-creates-provider and complicates authorization |
| Blocking deactivation when future appointments exist | Forces cancel-then-deactivate; inconsistent with the prospective-edit principle |
| Auto-cancelling appointments on deactivation | Destructive without notice; email is out of scope |
| Hard delete of accounts | Destroys history the brief requires |
| Mandatory reason on every admin action | Adds validation friction with no requirement behind it |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` Admin may cancel any `PENDING` or `CONFIRMED` appointment | Accepted |
| `[P]` Admin may not confirm, reject, complete, reschedule or edit operational data | Accepted |
| `[P]` Admin cancellation of a pending request yields `CANCELLED` | Accepted |
| `[P]` No role changes, no hard deletes | Accepted |
| `[P]` Deactivation with future appointments allowed; appointments surfaced | Accepted |
| `[P]` No self-deactivation; no deactivating the last active admin | Accepted |
| `[P]` Reasons prompted, not mandatory (A7) | Accepted |
| Exact provider profile fields editable by admin | U8 — proposed: name, category, contact, bio, activation |
| Admin list pagination | U4 — proposed: 20 per page |
