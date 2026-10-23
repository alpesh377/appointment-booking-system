# Requirements and Scope

| | |
|---|---|
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Source of truth** | Section 1 (assignment requirements) supersedes convenience; sections 3–5 are our decisions |

This document separates three things that are easy to conflate:

1. **Assignment requirements** (`[R]`) — stated in the brief. Must be delivered.
2. **Business-rule assumptions** (`[P]`, A-series) — values we invented because the brief is silent. Changeable.
3. **Exclusions** — deliberately out of scope, with the reasoning recorded.

Nothing in the A-series is required by the assignment. Nothing in the exclusion list is forbidden by it.

---

## 1. Assignment requirements

Requirement IDs are stable and referenced by the decision records.

### 1.1 Authentication and accounts — `[R]` 3.A

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-AUTH-1 | Registration | A visitor can create a customer account with email and password |
| R-AUTH-2 | Login / logout | Valid credentials produce a session; logout ends it |
| R-AUTH-3 | Profile management | A signed-in user can view and update their own profile |
| R-AUTH-4 | Three roles | Admin, Service Provider, Customer exist and are distinguishable |
| R-AUTH-5 | Role-based access | Each role reaches only the pages and API operations it is permitted |
| R-AUTH-6 | Protected pages | Unauthenticated or unauthorised access is rejected server-side, not just hidden |

### 1.2 Service provider management — `[R]` 3.B

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-PROV-1 | Provider listing | Customers can browse available (active) providers |
| R-PROV-2 | Provider profile | A provider detail page shows profile and service details |
| R-PROV-3 | Search | Providers are searchable by name and by service category |
| R-PROV-4 | Create provider | Admin can create a provider account |
| R-PROV-5 | Update provider | Admin and the provider themselves can update provider profile data |
| R-PROV-6 | Deactivate provider | Admin can deactivate a provider; the provider disappears from public listing |
| R-PROV-7 | Availability and duration display | Provider pages display availability information and appointment durations |

### 1.3 Availability management — `[R]` 3.C

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-AVL-1 | Working days and hours | A provider can configure which days they work and for how long |
| R-AVL-2 | Break times | A provider can define break periods excluded from availability |
| R-AVL-3 | Unavailable dates | A provider can mark specific dates unavailable |
| R-AVL-4 | Slot display | Customers see bookable slots for a chosen provider and date |
| R-AVL-5 | Availability updates | A provider can edit their availability after initial setup |
| R-AVL-6 | No bookings outside availability | A slot can never be booked outside effective working time |

### 1.4 Appointment booking — `[R]` 3.D

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-BOOK-1 | Select provider | Booking begins from a chosen provider |
| R-BOOK-2 | Select date and slot | Only currently valid slots are offered |
| R-BOOK-3 | Optional notes | The customer may attach notes to a booking |
| R-BOOK-4 | Confirmation | The customer receives a booking confirmation with details |
| R-BOOK-5 | Status display | Appointment status is visible wherever an appointment is shown |
| R-BOOK-6 | No overlapping bookings | A provider can never hold two active appointments covering the same instant |
| R-BOOK-7 | No unavailable slots | A slot on a break, a closed date, or outside hours cannot be created |

### 1.5 Appointment management — `[R]` 3.E

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-APPT-1 | Upcoming and past views | Appointments are separable into upcoming and past |
| R-APPT-2 | Customer cancel | A customer can cancel their own eligible appointment |
| R-APPT-3 | Customer reschedule | A customer can move their own eligible appointment to another valid slot |
| R-APPT-4 | Provider confirm | A provider can confirm a pending request |
| R-APPT-5 | Provider reject | A provider can reject a pending request |
| R-APPT-6 | Provider complete | A provider can mark a confirmed appointment completed |
| R-APPT-7 | Appointment details | Status, date, time, customer and provider details are displayed |
| R-APPT-8 | History | Past and terminal appointments remain retrievable |

### 1.6 Customer dashboard — `[R]` 3.F

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-CUST-1 | Upcoming list | The dashboard lists upcoming appointments |
| R-CUST-2 | Past and cancelled lists | Past and cancelled appointments are reachable |
| R-CUST-3 | Detail view | A single appointment can be opened in detail |
| R-CUST-4 | Search and filter | Appointments filterable by date and status |
| R-CUST-5 | Cancel / reschedule entry points | Eligible appointments expose those actions; ineligible ones do not |

### 1.7 Provider dashboard — `[R]` 3.G

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-PROVD-1 | Today's appointments | The provider sees the current day's appointments |
| R-PROVD-2 | Upcoming bookings | Future appointments are listed |
| R-PROVD-3 | Pending requests | Unanswered requests are visible and actionable |
| R-PROVD-4 | Status management | Confirm, reject and complete are available where legal |
| R-PROVD-5 | Availability management | Working hours, breaks and unavailable dates are editable from the dashboard |

### 1.8 Admin dashboard — `[R]` 3.H

| ID | Requirement | Acceptance criterion |
|---|---|---|
| R-ADMIN-1 | Totals | Counts of customers, providers and appointments are displayed |
| R-ADMIN-2 | Customer accounts | Customers can be listed and deactivated |
| R-ADMIN-3 | Provider management | Providers can be created, updated and deactivated |
| R-ADMIN-4 | All appointments | Every appointment is visible to the admin |
| R-ADMIN-5 | Filtering | Appointments filter by provider, customer, date and status |
| R-ADMIN-6 | Statistics | Aggregate appointment statistics are displayed |

### 1.9 UI — `[R]` 4

Ten pages are required: login, registration, provider listing, provider details, booking, booking confirmation, customer dashboard, provider dashboard, availability management, admin dashboard (user and appointment management may share the admin shell).

| ID | Requirement |
|---|---|
| R-UI-1 | Responsive layout on mobile and desktop |
| R-UI-2 | Loading indicators on asynchronous views |
| R-UI-3 | Validation messages on forms |
| R-UI-4 | Empty states wherever a list can be empty |
| R-UI-5 | Error messages that name the problem |

### 1.10 Technical and submission — `[R]` 5, 6

| ID | Requirement |
|---|---|
| R-TECH-1 | Next.js with TypeScript frontend |
| R-TECH-2 | Python FastAPI backend |
| R-TECH-3 | PostgreSQL database |
| R-TECH-4 | FastAPI Swagger / OpenAPI documentation |
| R-TECH-5 | A UI library or CSS framework |
| R-TECH-6 | Clear, maintainable code organisation |
| R-TECH-7 | Authentication and authorization implemented |
| R-TECH-8 | Frontend and backend correctly integrated |
| R-SUB-1 | Complete frontend and backend source code |
| R-SUB-2 | Database configuration and migration files |
| R-SUB-3 | README with setup and run instructions |
| R-SUB-4 | Environment variable example file |
| R-SUB-5 | API documentation |
| R-SUB-6 | Screenshots of the completed application |
| R-SUB-7 | Git repository containing the project |

---

## 2. Business-rule assumptions — `[P]`

These are **not** in the assignment. Each is a deliberate choice made where the brief is silent, and each may be changed without violating a requirement.

| ID | Assumption | Value | Rationale summary | Decided in |
|---|---|---|---|---|
| A1 | Minimum booking notice | `starts_at − now > 2h`, strict | Prevents same-minute bookings and keeps pending expiry coherent | D-003, D-004 |
| A2 | Booking horizon | 30 days ahead | Bounds availability queries | D-003 |
| A3 | Pending expiry | `min(created_at + 24h, starts_at − 2h)` | A pending request may not hold a slot indefinitely | D-004 |
| A4 | Customer cancel/reschedule cutoff | until `starts_at − 2h` | Anything bookable stays cancellable | D-004 |
| A5 | Service duration bounds | 15–480 minutes, multiples of 5 | Keeps generated grids sane | D-002 |
| A6 | DST policy | skip nonexistent local times, first occurrence for ambiguous | Deterministic and testable | D-007 |
| A7 | Cancellation reason | optional for all roles | Prompted in UI, never mandatory | D-004 |
| A8 | Schedule edit window | today and future dates only | Prevents meaningless history edits | D-003 |
| A9 | Reschedule scope | time only; provider and service fixed | One code path instead of two | D-004 |
| A10 | Rejected reschedule | does not restore the original booking | Follows from release-then-request | D-004 |
| A11 | Advisory lock timeout | 5 seconds, then HTTP 409 | Contention fails fast instead of hanging | D-005 |

---

## 3. Exclusions

Out of scope by decision. Each is either unnecessary for the requirements or would add an unstated rule.

| Excluded | Why |
|---|---|
| Payments and pricing | Never mentioned in the brief |
| Email notifications | No requirement; would require external infrastructure |
| Waitlists | Not required; adds a second queueing model |
| Provider self-registration | Admin creates providers (D-001) |
| `NO_SHOW` status | Deferred; keeps the status set at seven |
| Appointment buffers | Would invent an unstated duration |
| Automatic completion | Would fabricate an attestation (D-004) |
| Background scheduler / worker | All time-based rules are lazy or time-predicate based |
| Customer-timezone display conversion | Provider-local display with label (D-007) |
| Provider-configurable slot granularity | Duration-equals-step grid (D-003) |
| Multi-role accounts | One role per account (D-001) |
| Admin role changes | Bypasses admin-creates-provider (D-009) |
| Hard deletion of users, providers or services | History must survive (D-003, D-009) |
| Refresh-token rotation | Single-session cookie (U1) |
| Rate limiting | Not required at this scope |
| Audit log beyond `appointment_events` | The event table is the required history |

---

## 4. Open questions

Retained as **proposed defaults**, not blockers. They do not require another exploration round.

| ID | Question | Proposed resolution |
|---|---|---|
| U1 | Session lifetime and refresh strategy | Short-lived JWT in an `HttpOnly` cookie, re-login on expiry, no refresh tokens in v1 |
| U2 | Service category: free text or taxonomy | Free text with a suggested list; case-insensitive search |
| U3 | "Past" boundary for dashboards | `ends_at < now()`; in-progress counts as upcoming |
| U4 | Pagination and filter page size | Server-side pagination, 20 per page |
| U5 | Deployment target and local topology | `docker-compose` for Postgres plus both services in development; `Secure` cookies only in production |
| U6 | Password policy | Minimum 8 characters, Argon2id hashing |
| U7 | Seed data volume for screenshots | Small curated fixture set with a demo account per role |
| U8 | Scope of admin "edit provider" | Profile fields only — name, category, contact, bio, activation; not services or hours |
| U9 | Screenshots: manual or scripted | Manual capture during the final demonstration run |

---

## 5. Traceability

| Requirement group | Decisions |
|---|---|
| R-AUTH | D-001, D-006 |
| R-PROV | D-001, D-002, D-003 |
| R-AVL | D-003 |
| R-BOOK | D-002, D-003, D-004, D-005 |
| R-APPT | D-004, D-005, D-006 |
| R-CUST | D-004, D-006 |
| R-PROVD | D-003, D-004 |
| R-ADMIN | D-009 |
| R-UI | D-010 |
| R-TECH | D-006, D-010 |
| R-SUB | D-008, D-010 |

---

## 6. Definition of done

The project is complete when:

1. Every `R-*` acceptance criterion above is demonstrably satisfied.
2. The five mandatory test categories in D-008 pass against real PostgreSQL.
3. Alembic migrates an empty database to the final schema and back.
4. OpenAPI renders at `/docs` and covers every endpoint.
5. A clean machine can follow the README to a running application using `.env.example`.
6. Screenshots exist for each of the ten required pages.
