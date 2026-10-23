# Decision Records — Appointment Booking System

This folder is the permanent record of **why** the system is built the way it is. It is not the system specification.

| Source of truth | Scope |
|---|---|
| This folder (`docs/decisions/`) | Rationale, alternatives, trade-offs, assumptions, scope boundaries |
| OpenSpec (`openspec/`) | Proposed changes, system capabilities, requirements and scenarios |
| Application source | The implementation itself |

When the two disagree, the OpenSpec specification describes *what the system must do* and these records explain *why*. A change to a decision requires a new or amended record — never a silent edit.

---

## Status legend

| Status | Meaning |
|---|---|
| **Proposed** | Discussed, not approved. Not binding. |
| **Accepted** | Approved as the decision baseline. Binding until superseded. |
| **Rejected** | Considered and deliberately not adopted. Kept for context. |
| **Superseded** | Replaced by a later record. Kept for history. |

All records in this folder were **Accepted on 2026-10-23** as the v2 consolidated decision baseline.

## Label legend

| Label | Meaning |
|---|---|
| `[R]` | Assignment requirement — explicit in the assignment brief, must be delivered |
| `[P]` | Proposed scope addition or business-rule assumption — our decision, not stated in the brief |
| `[T]` | Technical choice — implementation approach, not a business rule |

The `[R]` / `[P]` distinction is load-bearing. Any behaviour labelled `[P]` is something we chose to add, and may be changed without violating the assignment. Behaviour labelled `[R]` may not be dropped.

---

## Index

| Document | Purpose |
|---|---|
| [requirements-and-scope.md](requirements-and-scope.md) | Assignment requirements, acceptance criteria, assumptions, exclusions |
| [architecture-overview.md](architecture-overview.md) | System architecture, module responsibilities, request flows, data model |
| [decision-log.md](decision-log.md) | One-line summary of every decision and its status |

### Decision records

| ID | Record | Title | Status | Date |
|---|---|---|---|---|
| D-001 | [001-identity-and-roles.md](001-identity-and-roles.md) | Identity and roles | Accepted | 2026-10-23 |
| D-002 | [002-provider-services-and-duration.md](002-provider-services-and-duration.md) | Provider services and duration | Accepted | 2026-10-23 |
| D-003 | [003-availability-and-slot-generation.md](003-availability-and-slot-generation.md) | Availability and slot generation | Accepted | 2026-10-23 |
| D-004 | [004-appointment-lifecycle.md](004-appointment-lifecycle.md) | Appointment lifecycle | Accepted | 2026-10-23 |
| D-005 | [005-concurrency-and-booking-integrity.md](005-concurrency-and-booking-integrity.md) | Concurrency and booking integrity | Accepted | 2026-10-23 |
| D-006 | [006-authentication-and-authorization.md](006-authentication-and-authorization.md) | Authentication, authorization and CSRF | Accepted | 2026-10-23 |
| D-007 | [007-timezones.md](007-timezones.md) | Timezone handling | Accepted | 2026-10-23 |
| D-008 | [008-testing-strategy.md](008-testing-strategy.md) | Testing strategy | Accepted | 2026-10-23 |
| D-009 | [009-admin-supervisory-powers.md](009-admin-supervisory-powers.md) | Admin supervisory powers | Accepted | 2026-10-23 |
| D-010 | [010-application-architecture-and-stack.md](010-application-architecture-and-stack.md) | Application architecture and stack | Accepted | 2026-10-23 |

---

## Reading order

For a newcomer:

1. `requirements-and-scope.md` — what must be built and what is deliberately excluded.
2. `architecture-overview.md` — how the pieces fit.
3. `decision-log.md` — skim every decision at a glance.
4. Individual records — read the ones relevant to the work at hand.

## Rule for changing a decision

1. Create a new record or amend the existing one.
2. Set the old record's status to `Superseded` and link forward.
3. Explain what changed and why in the new record.
4. Never delete the previous reasoning; history is part of the record's value.
