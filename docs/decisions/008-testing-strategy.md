# 008 — Testing Strategy

| | |
|---|---|
| **Decision ID** | D-008 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 5 (correct integration, error handling), 6 (migration files, API documentation), evaluation criteria for error handling and validation |
| **Scope additions** | `[P]` explicit test categories, real-PostgreSQL requirement, exclusion of broad E2E and load testing |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The assignment does not require tests. It does require correct error handling, validation, database migrations and API documentation, and it evaluates booking correctness. Those are precisely the areas where a successful demo proves nothing: nobody clicks two buttons at the same millisecond, and DST only matters twice a year.

The strategy is therefore narrow and targeted rather than broad. Five categories carry almost all the risk; everything else is optional.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-BOOK-6 | Requires concurrency evidence, not just an implementation |
| R-AVL-6 | Requires slot-engine evidence |
| R-AUTH-5 / 6 | Requires an authorization matrix |
| R-APPT-* | Requires transition coverage |
| R-SUB-2 | Migrations must be verifiable |
| R-SUB-5 | OpenAPI must generate |
| Evaluation criteria | "Error handling and validation" is explicitly graded |

---

## 3. Options considered

| Option | Coverage | Cost |
|---|---|---|
| No tests | Zero evidence for the graded risks | Cheapest, weakest |
| Broad unit + full E2E | High breadth, shallow on concurrency | High, and slow to maintain |
| **Five targeted categories + supporting checks (selected)** | Deep where risk concentrates | Moderate |
| SQLite-based tests | Fast, but cannot exercise the exclusion constraint | Misleading |

---

## 4. Selected approach

### 4.1 Mandatory categories

| # | Category | Cases |
|---|---|---|
| 1 | **Slot engine (unit)** | Window composition; multiple windows per weekday; weekly and date-specific breaks; closed overrides; override windows replacing weekly rules; duration fitting; grid anchoring at window start; unused tail; 30-day horizon; strict 2-hour notice boundary; empty results; DST spring and fall |
| 2 | **Concurrency (PostgreSQL)** | Two parallel bookings on one slot → exactly one `201` and one `409`; concurrent reschedule swap; expiry racing a booking; duplicate submission; per-path coverage of the D-005 protocol |
| 3 | **Authorization matrix** | Role × endpoint × ownership, parametrized; deactivated accounts rejected; cross-customer and cross-provider access denied |
| 4 | **State transitions** | Every legal edge in D-004; every illegal edge; terminal-state immutability for all roles including admin; `409 USE_REJECT`; cancellation cutoff boundaries; completion before and after `ends_at` |
| 5 | **Reschedule atomicity** | Conflict leaves the original unchanged; success leaves exactly one active successor; links set in both directions; a rejected successor leaves the predecessor `RESCHEDULED` |

### 4.2 Supporting checks

| Check | Reason |
|---|---|
| Alembic upgrade and downgrade on an empty database | Migrations are an explicit deliverable |
| OpenAPI schema generation without error | Swagger is an explicit deliverable |
| Admin seed command smoke test | The only way to obtain an admin account |
| CSRF: missing `Origin`, wrong `Origin`, missing token, mismatched token, correct pair, safe-method exemption | Defence-in-depth is unverifiable without it |
| Validation: duration bounds, non-multiple-of-5 rejection, notes length, invalid status values | Graded criterion |

### 4.3 Database requirement

Integration and concurrency tests run against **real PostgreSQL**. SQLite is not acceptable because the system depends on:

- `EXCLUDE USING gist` and `btree_gist`,
- `tstzrange` overlap semantics,
- `citext` uniqueness,
- advisory locks.

Testing on SQLite would validate a different system than the one deployed.

### 4.4 Optional

- One Playwright end-to-end happy path: register → admin creates provider → provider sets hours → customer books → provider confirms → provider completes. Undertaken only if time permits.

### 4.5 Out of scope

- Load and performance testing.
- Exhaustive end-to-end coverage of every page.
- Broad frontend unit testing.
- Coverage percentage targets. The five categories are the bar, not a number.

---

## 5. Reasons

- The five categories map directly onto the areas you asked to protect: availability, state transitions and double booking.
- Real PostgreSQL is the only environment where the actual guarantees exist.
- The remaining checks cover the explicit submission deliverables (migrations, OpenAPI) and the newly added CSRF layer.
- Deliberately excluding broad E2E keeps the suite fast enough to actually run.

---

## 6. Advantages and disadvantages

### Advantages

- Every high-risk guarantee has a named test that would fail if the guarantee broke.
- Concurrency tests double as executable documentation of D-005.
- The suite stays small enough to run on every change.
- Migration and OpenAPI checks protect two explicitly graded deliverables.

### Disadvantages

- Requires a provisioned PostgreSQL instance in the test path.
- No coverage number, so the suite can silently miss untested UI behaviour.
- Frontend behaviour is largely verified manually.
- Optional Playwright coverage may never be written, leaving the happy path unproven end-to-end.

---

## 7. Implications

**Security.** The authorization matrix is the primary evidence that protected pages are actually protected. CSRF tests prove the four layers are wired, not merely configured.

**Data integrity.** Concurrency and atomicity tests are the only way to demonstrate the exclusion constraint and the advisory-lock protocol behave as designed.

**Performance.** The suite is small; no performance budget is asserted.

**Testing.** Transactional rollback per test for most cases; concurrency tests need real commits and therefore a separate fixture with truncation between tests.

---

## 8. Consequences for architecture and future changes

- The slot engine must remain a pure function, or category 1 becomes hard to write. This constraint is already reflected in D-003.
- Test fixtures must be able to construct providers, services, availability and appointments directly through services or repositories.
- `docker-compose` (U5) should include a test database, or the README must document how to point tests at one.
- New appointment-mutating endpoints are expected to add a case to categories 2 and 4.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| SQLite test database | Cannot exercise the constraint, advisory locks or `citext` |
| Full end-to-end coverage | Slow, brittle, and redundant with the targeted categories |
| Coverage percentage target | Encourages low-value tests; the named categories are a better bar |
| Load testing | No performance requirement |
| Mocking the database for concurrency tests | Would test the mock, not the constraint |
| Frontend test suite as a deliverable | No requirement; manual verification of the happy path is sufficient at this scope |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` Five mandatory categories | Accepted |
| `[P]` Real PostgreSQL for integration and concurrency tests | Accepted |
| `[P]` Playwright happy path optional | Accepted |
| `[P]` No coverage target, no load testing, no broad E2E | Accepted |
| Test database provisioning approach | U5 — proposed: `docker-compose` includes a test database |
| Framework specifics (pytest, httpx AsyncClient, fixture strategy) | Implementation detail |
