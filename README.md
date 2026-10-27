# Appointly — appointment booking system

A full-stack appointment booking application. Customers discover service providers and book
appointments, providers manage their services, availability and appointment lifecycle, and
administrators oversee accounts and the whole platform.

The behaviour is defined by the accepted decision records in [`docs/decisions/`](docs/decisions/)
and the OpenSpec change in
[`openspec/changes/appointment-booking-system/`](openspec/changes/appointment-booking-system/).

- **Frontend:** Next.js (App Router) + TypeScript, Tailwind CSS v4, shadcn/ui primitives, React
  Hook Form + Zod, TanStack Query, Motion
- **Backend:** Python FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic
- **Database:** PostgreSQL 16 with `btree_gist`, `citext`, `timestamptz` and an exclusion constraint

## Prerequisites

| Tool | Version |
|---|---|
| Docker (with Compose) | any recent release |
| Python | 3.12 or newer |
| Node.js | 20 or newer (22 used here) |
| npm | 10 or newer |

The UI targets the Tailwind CSS v4 browser baseline: Safari 16.4+, Chrome 111+ and Firefox 128+.

## Quick start

Run every command from the repository root unless a step says otherwise.

### 1. Environment

```bash
cp backend/.env.example backend/.env
```

The defaults work for local development. Admins are seeded from `ADMIN_EMAIL`, `ADMIN_PASSWORD`
and `ADMIN_NAME`; there is no default password in migrations or code.

Key settings:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL for PostgreSQL |
| `APP_ORIGIN` | The browser origin; must match the frontend URL (`http://localhost:3000`) |
| `JWT_SECRET` | Signing secret for the session cookie |
| `JWT_TTL_MINUTES` | Session lifetime |
| `COOKIE_SECURE` | `false` for local HTTP, `true` in production |
| `APP_ENV` | `development` locally; production refuses the development JWT secret and `COOKIE_SECURE=false` |
| `LOG_LEVEL` | Application log level (`INFO` by default) |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` | First administrator created by the setup command |
| `SCHEDULING_HORIZON_DAYS` / `BOOKING_NOTICE_HOURS` / `PENDING_HOLD_HOURS` | Documented business-rule assumptions |
| `BACKEND_URL` (frontend, optional) | Rewrite target for `/api/*`; defaults to `http://127.0.0.1:8000` |

### 2. Database

```bash
docker compose up -d db
```

### 3. Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt   # runtime + test/lint/security tools
./.venv/bin/alembic upgrade head
./.venv/bin/python -m app.seed
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

Use `requirements.txt` alone for a runtime-only install. Versions are pinned with compatible-release
specifiers so installations stay reproducible without a separate lock file.

- API: <http://localhost:8000/api>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI schema: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/api/health>

`python -m app.seed` creates exactly one active administrator, is safe to run twice, and exits with
a clear error when `ADMIN_EMAIL` or `ADMIN_PASSWORD` is missing.

### 4. Frontend

```bash
cd frontend
npm ci
npm run dev
```

Open <http://localhost:3000>. The browser talks only to the Next.js origin; `rewrites` forwards
`/api/*` to FastAPI so the `HttpOnly` session cookie and CSRF checks stay same-origin.

### 5. First run in the browser

1. Sign in as the seeded administrator and create a provider account under **Users**.
2. Sign in as that provider, add services under **Services**, then configure **Availability**
   (working windows, breaks, optional date overrides).
3. Register a customer account, choose the provider, pick a service, date and slot.
4. Sign back in as the provider to confirm or reject the pending request, and mark it completed
   once its end time has passed.

## Tests

The suite runs against **real PostgreSQL**, because the overlap guarantee depends on an exclusion
constraint that SQLite cannot express.

```bash
docker compose exec db createdb -U abs appointment_booking_test   # once
cd backend
./.venv/bin/python -m pytest
./.venv/bin/python -m pytest --cov=app --cov-report=term-missing   # coverage
./.venv/bin/ruff check app tests
./.venv/bin/ruff format --check app tests
./.venv/bin/bandit -c pyproject.toml -r app
./.venv/bin/pip-audit
```

Frontend checks:

```bash
cd frontend
npm run lint        # ESLint 9 flat config with next/core-web-vitals + next/typescript
npm run typecheck   # tsc --noEmit
npm run build       # production build
```

Coverage maps to the five mandatory categories in
[D-008](docs/decisions/008-testing-strategy.md):

| Category | Test files |
|---|---|
| Slot engine and timezones | `test_slot_engine.py` |
| Booking, expiry and concurrency | `test_booking.py`, `test_reschedule.py` |
| Lifecycle transitions | `test_lifecycle.py` |
| Authentication, authorization and CSRF | `test_auth_csrf.py`, `test_providers.py`, `test_admin.py` |
| Schema constraints and migrations | `test_schema_constraints.py`, `test_platform.py` |

`test_platform.py` also covers Alembic up/down, OpenAPI generation and the administrator setup command.

## Database migrations

```bash
cd backend
./.venv/bin/alembic upgrade head      # apply
./.venv/bin/alembic downgrade base    # roll back everything
```

The initial revision enables `btree_gist` and `citext`, creates the schema, indexes, check
constraints and the exclusion constraint that prevents overlapping active appointments per provider.

## Architecture

```
backend/app/
  api/            routers by resource and role
  core/           config, security, CSRF middleware, errors, time helpers
  models/         SQLAlchemy models and constraints
  schemas/        Pydantic request models
  services/       slot engine, booking, lifecycle, providers, administration
  repositories/   queries, transactions, advisory locks
  tests/          pytest suite
frontend/src/
  app/            routes: public, customer, provider, admin
  components/     shared UI, shadcn/ui primitives, dialogs, motion wrapper
  lib/            HTTP wrapper, formatting, types, Zod schemas, form-error mapping
  middleware.ts   UX-only redirects for protected routes
docs/decisions/   accepted decision baseline
docs/screenshots/ required screenshots
openspec/         proposal, capability specs, design and tasks
```

### Frontend stack

- shadcn/ui primitives live in `components/ui` and are registered in `components.json` for the
  current Next.js 15 and Tailwind CSS v4 setup (CSS-first `@theme` tokens in `globals.css`);
  Radix provides dialog, alert-dialog, label and slot behaviour.
- Forms use React Hook Form with Zod schemas from `lib/validation.ts` and the shadcn `Form`
  primitives, so labels, `aria-invalid`, descriptions and messages stay wired together. FastAPI
  field errors are copied onto the matching fields by `lib/form-errors.ts`.
- TanStack Query owns server state: queries key on the role and filters, and every mutation
  invalidates affected queries. Authentication state stays in the existing React context, so no
  global store is needed.
- Motion supplies short, reduced-motion-aware entrances; `MotionConfig reducedMotion="user"`
  disables them when the operating system asks for reduced motion.

### Request path and security

- FastAPI is the only authorization authority. Every protected operation checks authentication,
  role and ownership server-side.
- The session is a JWT in an `HttpOnly`, `SameSite=Lax` cookie (`__Host-` prefixed in production).
- State-changing requests require a matching `Origin` **and** the `csrf_token` cookie echoed in
  `X-CSRF-Token`. The frontend's single HTTP wrapper adds the header; safe methods are exempt.
- Deactivated accounts fail authentication while their appointment history remains intact.
- Errors use stable codes such as `SLOT_UNAVAILABLE`, `INVALID_TRANSITION`, `USE_REJECT`,
  `CSRF_TOKEN_INVALID` and `CUTOFF_PASSED`.

### Concurrency

Every appointment mutation acquires `pg_advisory_xact_lock(provider_id)`, sweeps expired pending
requests, re-validates against committed state, then mutates and appends events in one transaction.
PostgreSQL additionally enforces non-overlap with:

```sql
EXCLUDE USING gist (provider_id WITH =, tstzrange(starts_at, ends_at) WITH &&)
  WHERE (status IN ('PENDING','CONFIRMED'))
```

### Time and availability

- Working windows, breaks and overrides are wall-clock times in the provider's IANA timezone.
- Slots are anchored at each effective window start and advance by the service duration.
- Non-existent local times are skipped; ambiguous times use the first occurrence.
- Availability is always derived, never stored, and bounded by a 30-day horizon and a strict
  2-hour notice period. All displayed times carry the provider's timezone label.

## Screenshots

| Page | Image |
|---|---|
| Sign in | [`01-login.png`](docs/screenshots/01-login.png) |
| Registration | [`02-register.png`](docs/screenshots/02-register.png) |
| Provider listing | [`03-provider-listing.png`](docs/screenshots/03-provider-listing.png) |
| Provider details | [`04-provider-detail.png`](docs/screenshots/04-provider-detail.png) |
| Booking | [`05-booking.png`](docs/screenshots/05-booking.png) |
| Booking confirmation | [`06-booking-confirmation.png`](docs/screenshots/06-booking-confirmation.png) |
| Customer dashboard | [`07-customer-dashboard.png`](docs/screenshots/07-customer-dashboard.png) |
| Provider dashboard | [`08-provider-dashboard.png`](docs/screenshots/08-provider-dashboard.png) |
| Availability management | [`09-availability.png`](docs/screenshots/09-availability.png) |
| Admin dashboard | [`10-admin-dashboard.png`](docs/screenshots/10-admin-dashboard.png) |
| Admin user management | [`11-admin-users.png`](docs/screenshots/11-admin-users.png) |
| Admin appointment management | [`12-admin-appointments.png`](docs/screenshots/12-admin-appointments.png) |
| Provider service management | [`13-provider-services.png`](docs/screenshots/13-provider-services.png) |

## Decision records

Start with [`docs/decisions/README.md`](docs/decisions/README.md) and the summary
[`decision-log.md`](docs/decisions/decision-log.md).

| ID | Subject |
|---|---|
| [D-001](docs/decisions/001-identity-and-roles.md) | Identity, roles and account creation |
| [D-002](docs/decisions/002-provider-services-and-duration.md) | Provider services and durations |
| [D-003](docs/decisions/003-availability-and-slot-generation.md) | Availability and slot generation |
| [D-004](docs/decisions/004-appointment-lifecycle.md) | Appointment lifecycle |
| [D-005](docs/decisions/005-concurrency-and-booking-integrity.md) | Concurrency and booking integrity |
| [D-006](docs/decisions/006-authentication-and-authorization.md) | Authentication, authorization and CSRF |
| [D-007](docs/decisions/007-timezones.md) | Timezones |
| [D-008](docs/decisions/008-testing-strategy.md) | Testing strategy |
| [D-009](docs/decisions/009-admin-supervisory-powers.md) | Administrator powers |
| [D-010](docs/decisions/010-application-architecture-and-stack.md) | Architecture and stack |

## Known limitations (accepted)

- No background worker: pending expiry and time-based rules are applied lazily.
- No static Python type checker is configured; Pydantic and SQLAlchemy models plus Ruff and the
  test suite provide the current safety net.
- Completion is never automatic; a provider must record it.
- Times are displayed in the provider's timezone with a label; customer-timezone conversion is out of scope.
- The duration-equals-step grid can leave up to `duration − 1` minutes unused at the end of a window.
- Administrators may cancel appointments but cannot confirm, reject, complete or reschedule them.
- No payments, email notifications, waitlists, provider self-registration or hard deletion of history.
