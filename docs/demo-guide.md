# Demo & test guide

How to run Appointly, show it to someone else, and prove the important rules work.

There are three ways to use this document:

| You have | Use |
|---|---|
| 5 minutes and pre-created accounts | [Five-minute highlight](#five-minute-highlight) |
| 20–30 minutes | [Full role-by-role walkthrough](#full-walkthrough) |
| A technical audience | Add the [automated evidence](#automated-evidence) and [rules worth proving](#rules-worth-proving) |

---

## 1. Before the demo

### Prerequisites

- Docker with Compose
- Python 3.12+
- Node.js 20+ and npm 10+

### Start the stack

Use three terminals, all from the repository root.

**Terminal 1 — database**

```bash
docker compose up -d db
```

**Terminal 2 — API**

```bash
cd backend
./.venv/bin/alembic upgrade head
./.venv/bin/python -m app.seed
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

If `backend/.venv` does not exist yet:

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
```

**Terminal 3 — web app**

```bash
cd frontend
npm ci
npm run dev
```

If dependencies are already installed, `npm run dev` is enough.

### Verify before anyone is watching

```bash
curl -s http://localhost:8000/api/health
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3000
```

Expected: `{"status":"ok","environment":"development"}` and `200`.

| What | URL |
|---|---|
| Web app | <http://localhost:3000> |
| API | <http://localhost:8000/api> |
| Swagger UI | <http://localhost:8000/docs> |
| Health | <http://localhost:8000/api/health> |

### Accounts

The administrator is created by the seed command from `backend/.env`:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@example.com` | `admin-password-123` |

Providers cannot self-register. The admin creates them. Customers register themselves. Both are
created during the walkthrough, so you choose the passwords and always know them.

> If `python -m app.seed` prints “Administrator … already exists”, that is success — it is
> idempotent. It only fails when `ADMIN_EMAIL` or `ADMIN_PASSWORD` is missing or the password is
> shorter than 8 characters.

### Clean slate (optional)

Do this if the database contains old test data and you want the admin dashboard totals to look
tidy. **Stop the API first** (Ctrl+C in Terminal 2), then:

```bash
cd backend
./.venv/bin/alembic downgrade base
./.venv/bin/alembic upgrade head
./.venv/bin/python -m app.seed
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

This deletes all users, services, availability and appointments, then recreates the administrator.
The Docker volume is kept.

### Prep once, if you only have five minutes

**Only for the five-minute version.** The full walkthrough creates its own accounts, so skip this
section if you are using that instead.

Before the audience arrives:

1. Sign in as the admin.
2. **Users → Create a provider account**
   - Email: `maya@example.com`
   - Initial password: `provider-demo-123`
   - Full name: `Maya Chen`
   - Display name: `Maya Chen Physiotherapy`
   - Category: `Physiotherapy`
   - IANA timezone: `Europe/London` (or your local zone)
   - **Create provider**
3. Sign out, sign in as `maya@example.com`.
4. **Services → Add a service**
   - Name: `Initial consultation`
   - Category: `Physiotherapy`
   - Duration: `30`
   - **Add service**
5. **Availability → Working windows**
   - **Add window** for every weekday you want bookable, each `09:00`–`17:00`
   - **Save windows**
6. Sign out, **Register** a customer: `demo@example.com` / `customer-demo-123`.

Now the five-minute demo can jump straight to booking.

---

## Five-minute highlight

This is a read-aloud script. It assumes the [prep](#prep-once-if-you-only-have-five-minutes) is
done and everyone is signed out.

| Time | Do this | Say / point out |
|---|---|---|
| 0:00 | Open <http://localhost:3000> | “This is the public directory. Only active providers appear, and each card shows the service durations on offer.” |
| 0:30 | Search for `Maya`, open the provider | “Times are always shown in the provider's own timezone, with the zone named.” |
| 0:50 | Click **Book this service →** | “The customer picks a service, then a date. The slot grid is generated from the provider's working windows and the service duration.” |
| 1:10 | Sign in as `demo@example.com` / `customer-demo-123` | “Booking requires a customer account.” |
| 1:30 | Pick tomorrow, choose a slot, add a note, **Request appointment** | “This creates a **Pending** request — not a confirmed booking. The slot is held so nobody else can take it.” |
| 2:10 | Show the confirmation page | Point at the pending banner, the hold expiry, and the timezone label. |
| 2:30 | Sign out, sign in as `maya@example.com` / `provider-demo-123` | “The provider sees the request on their dashboard.” |
| 2:50 | **Pending requests → Confirm** | “The customer can now see it as confirmed.” |
| 3:20 | Sign out, sign back in as the customer, open **My appointments** | “Upcoming, Past and Cancelled are separate views; history is never deleted.” |
| 3:50 | Open the appointment | Point at the status, history, and available actions. |
| 4:20 | Sign in as `admin@example.com` / `admin-password-123`, open **Overview** and **Appointments** | “Admins see platform totals and every appointment, including those of deactivated accounts.” |
| 4:50 | Open <http://localhost:8000/docs> | “The whole API is documented, and the backend has 163 automated tests.” |

If you have two more minutes, demonstrate **Reschedule**: as the customer, open the confirmed
appointment, pick a new date and time, and click **Reschedule to selected time**.

---

## Full walkthrough

Timing below is approximate for a 20–30 minute session. Each stage ends with what the audience
should observe.

### Stage 1 — Admin sets up the platform (5 min)

1. Sign in at <http://localhost:3000/login> as `admin@example.com` / `admin-password-123`.
2. Open **Overview**. Point out:
   - totals for users, providers, services and appointments;
   - the “Appointments by status” breakdown.
3. Open **Users**.
   - The **Customers** table lists self-registered customers.
   - The **Providers** table lists provider accounts and profiles.
4. Under **Create a provider account**, create a second provider live:
   - Email: `sam@example.com`
   - Initial password: `provider-demo-123`
   - Full name: `Sam Rivera`
   - Display name: `Sam Rivera Nutrition`
   - Category: `Nutrition`
   - IANA timezone: `Europe/Rome`
   - **Create provider**
5. Point out that the new provider appears in the table. After signing in and adding at least one
   service and a working window, the provider becomes bookable.
6. Show the **Deactivate** action on a customer or provider, but do not confirm it yet — Stage 6
   demonstrates it deliberately.

**Observable result:** the provider account exists and can sign in. There is still no public
provider self-registration, by design.

### Stage 2 — Provider configures services and availability (6 min)

1. Sign out and sign in as `maya@example.com` / `provider-demo-123`.
2. Open **Services**.
   - Add a 30-minute service: `Initial consultation`, category `Physiotherapy`.
   - Add a 60-minute service: `Follow-up session`, category `Physiotherapy`.
   - Point out the rule shown on the page: durations are 15–480 minutes in steps of 5.
3. Open **Availability**.
   - **Working windows:** add one `09:00`–`17:00` window for each weekday you want bookable
     (at minimum, tomorrow's weekday). Click **Save windows**.
   - Optional: add a recurring break `12:00`–`13:00` and click **Save breaks**.
   - Optional: add a date override for a specific date, mark it **Closed**, and click
     **Save overrides**.
   - Under **Practice details**, confirm the timezone and click **Save practice details**.
4. Explain the behaviour while the page is open:
   - availability is derived, never stored;
   - slots start at each window start and advance by the service duration;
   - non-existent local times at a DST jump are skipped; ambiguous times use the first occurrence;
   - bookings are limited to a 30-day horizon and a strict 2-hour notice period.

**Observable result:** the same working day produces a different number of slots for the 30-minute
and 60-minute services.

### Stage 3 — Customer books (5 min)

1. Sign out. Click **Register** and create a customer:
   - Full name: `Demo Customer`
   - Email: `customer@example.com`
   - Phone: optional
   - Password: `customer-demo-123`
2. From **Providers**, search for `Maya` and open the profile.
3. Click **Book this service →** next to `Initial consultation`.
4. Choose tomorrow's date (or another date with a working window).
   - Point out the slot groups: Morning, Afternoon, Evening.
   - Pick a slot, add a note, click **Request appointment**.
5. On the confirmation page, point out:
   - status **Pending**;
   - the sentence explaining the slot is held;
   - the hold expiry (`min(created + 24h, start − 2h)`);
   - the provider timezone label.
6. Open **My appointments**.
   - **Upcoming** contains the pending request.
   - **Past** and **Cancelled** are separate views.
   - The status and date filters work.
7. Book a second appointment at a different time. Keep it for the reschedule and cancellation
   demos.
8. Prove the hold live: sign out, register a second customer
   (`rival@example.com` / `customer-demo-123`), open the same provider and date. The slot booked in
   step 4 is no longer offered.

**Observable result:** a pending request removes its slot from everyone else's grid.

### Stage 4 — Provider confirms and rejects (4 min)

1. Sign in as `maya@example.com`.
2. On **Dashboard**, locate **Pending requests**.
3. **Confirm** the first request.
   - It moves to **Upcoming**.
   - The customer now sees **Confirmed**.
4. **Reject** the second request and enter a short reason.
   - It moves out of the active lists and is recorded as **Rejected**.
   - The slot becomes bookable again.
5. Open the rejected appointment's detail page to show the reason and history.
6. Point out that a pending request only offers **Confirm** and **Reject** — there is no
   **Cancel**. The API enforces the same rule with `409 USE_REJECT`. Explain that pending and
   confirmed have different terminal transitions.
7. Explain completion:
   - **Mark completed** only appears for a confirmed appointment whose end time has passed;
   - completion is never automatic.

**Observable result:** confirm and reject both free the pending hold in different ways, and the
customer sees the outcome immediately.

### Stage 5 — Customer reschedules (4 min)

1. Sign in as `customer@example.com`.
2. Open the **Confirmed** appointment (more than 2 hours before it starts).
3. In the **Reschedule** panel, choose a new date and time and click
   **Reschedule to selected time**.
4. Point out the result:
   - the original becomes **Rescheduled**;
   - a new **Pending** appointment is created for the new time;
   - the detail pages link to each other (“Rescheduled from…” / “Rescheduled to…”);
   - the new time still needs provider confirmation.
5. Sign in as the provider and confirm the new request.
6. Explain the integrity guarantee:
   - every mutation takes a per-provider advisory lock;
   - the original slot and the new slot are swapped in one transaction;
   - a PostgreSQL exclusion constraint backs this up, so two active appointments can never overlap.

**Observable result:** rescheduling is a linked chain, not an edit in place, and no slot is lost or
double-booked.

### Stage 6 — Admin supervision and account state (3 min)

1. Sign in as the admin.
2. Open **Appointments**.
   - Filter by status, provider, customer and date range.
   - Open a pending or confirmed appointment and **Cancel** it with a reason.
   - On the detail page, **Cancelled by** shows `ADMIN`.
3. Point out what the admin cannot do:
   - no **Confirm**, **Reject**, **Complete** or **Reschedule** buttons;
   - the API returns `403` for those actions;
   - admins cannot edit provider services or availability.
4. Open **Users** and deactivate `customer@example.com` (the customer with appointments).
   - They can no longer sign in.
   - Their appointment history remains intact and visible to the admin.
5. Deactivate `maya@example.com`.
   - She disappears from the public directory, so new customers cannot book her.
   - Existing and future appointments remain, and the admin still sees them.
6. Reactivate both to leave the demo environment usable.

**Observable result:** administrative power is supervisory, not operational, and deactivation never
deletes history.

---

## Rules worth proving

Some rules are hard to stage live because they depend on time or races. Use the test suite for
those — it runs against real PostgreSQL.

| Rule | How to show it | Expected |
|---|---|---|
| Slots follow service duration | Book the 30-min and 60-min services on the same day | Different slot grids |
| A pending request holds its slot | Second customer opens the same date | The slot is absent |
| Overlap is impossible | `pytest tests/test_booking.py::test_concurrent_bookings_yield_exactly_one_success -v` | Exactly one success |
| Database also refuses overlap | `pytest tests/test_booking.py::test_database_rejects_overlapping_active_appointments -v` | Constraint violation |
| Reject, don't cancel, a pending request | `pytest tests/test_lifecycle.py::test_provider_must_reject_not_cancel_a_pending_request -v` | `409 USE_REJECT` |
| Customer cutoff is 2 hours | `pytest tests/test_lifecycle.py::test_customer_cannot_cancel_inside_the_cutoff -v` | `403 CUTOFF_PASSED` |
| Pending requests expire lazily | `pytest tests/test_booking.py::test_expired_pending_releases_its_slot_and_is_recorded -v` | Slot released, event recorded |
| Near-term hold ends 2 hours before start | `pytest tests/test_booking.py::test_near_term_hold_expires_two_hours_before_the_start -v` | Hold is capped |
| Completion requires the end time | `pytest tests/test_lifecycle.py::test_completion_requires_the_end_time_to_have_passed -v` | Refused before end |
| Completion is never automatic | `pytest tests/test_lifecycle.py::test_a_past_confirmed_appointment_is_not_completed_automatically -v` | Stays confirmed |
| Reschedule claims the new slot atomically | `pytest tests/test_reschedule.py::test_reschedule_rejects_a_taken_slot_atomically -v` | No partial swap |
| Concurrent reschedules produce one successor | `pytest tests/test_reschedule.py::test_concurrent_reschedules_produce_one_successor -v` | One successor |
| Role checks are server-side | `pytest tests/test_auth_csrf.py::test_role_endpoint_matrix -v` | Matrix passes |
| CSRF is enforced | `pytest tests/test_auth_csrf.py::test_csrf_rejects_missing_or_mismatched_token -v` | Rejected |
| DST and timezones are handled | `pytest tests/test_slot_engine.py -v` | All pass |
| Migrations apply and reverse | `pytest tests/test_platform.py::test_migrations_apply_and_reverse_cleanly -v` | Clean up/down |

---

## Automated evidence

### Backend

The suite needs real PostgreSQL because the overlap guarantee uses an exclusion constraint that
SQLite cannot express. Create the test database once:

```bash
docker compose exec db createdb -U abs appointment_booking_test
```

Ignore “already exists” on later runs. Then:

```bash
cd backend
./.venv/bin/python -m pytest -q
```

Expected at the time of writing: **163 passed**. The full run takes about 80 seconds.

Focused runs and quality gates:

```bash
cd backend

# one category
./.venv/bin/python -m pytest tests/test_lifecycle.py -v
./.venv/bin/python -m pytest tests/test_booking.py tests/test_reschedule.py -v

# coverage
./.venv/bin/python -m pytest --cov=app --cov-report=term-missing

# lint, format, security, dependencies
./.venv/bin/ruff check app tests
./.venv/bin/ruff format --check app tests
./.venv/bin/bandit -c pyproject.toml -r app
./.venv/bin/pip-audit
```

Coverage maps to the five mandatory categories in
[`docs/decisions/008-testing-strategy.md`](decisions/008-testing-strategy.md):

| Category | Test files |
|---|---|
| Slot engine and timezones | `test_slot_engine.py` |
| Booking, expiry and concurrency | `test_booking.py`, `test_reschedule.py` |
| Lifecycle transitions | `test_lifecycle.py` |
| Authentication, authorization and CSRF | `test_auth_csrf.py`, `test_providers.py`, `test_admin.py` |
| Schema constraints and migrations | `test_schema_constraints.py`, `test_platform.py` |

`test_availability.py` covers the slot grid through the HTTP API. `test_platform.py` also covers
Alembic up/down, OpenAPI generation and the seed command.

### Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm run build
```

Expected: no lint errors, no type errors, and a successful production build listing all routes.

### API smoke check

With the API running:

```bash
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/providers
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/openapi.json
```

Expected: `status: ok`, a JSON array of active providers, and `200`.

> State-changing API calls need the session cookie **and** the CSRF cookie echoed in the
> `X-CSRF-Token` header, and `Origin` must match `APP_ORIGIN`. The browser app does this
> automatically. Swagger UI is useful for reading the API; for writes, use the app or the curl
> flow below.

```bash
# 1. Make a safe request to receive the csrf_token cookie
curl -s -c cookies.txt http://localhost:8000/api/providers >/dev/null
TOKEN=$(awk '$6=="csrf_token" {print $7}' cookies.txt)

# 2. Sign in (Origin must match APP_ORIGIN in backend/.env)
curl -s -b cookies.txt -c cookies.txt \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $TOKEN" \
  -H 'Origin: http://localhost:3000' \
  -X POST http://localhost:8000/api/auth/login \
  -d '{"email":"admin@example.com","password":"admin-password-123"}'

# 3. Reuse the session cookie for authenticated reads
curl -s -b cookies.txt http://localhost:8000/api/auth/me
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `connection refused` on port 5432 | Database not up yet | `docker compose ps`; wait for `healthy` |
| `database "appointment_booking" does not exist` | Volume was removed or first run | `docker compose up -d db`, then `./.venv/bin/alembic upgrade head` |
| `alembic: command not found` | Virtualenv not active | Use `./.venv/bin/alembic` from `backend/` |
| Seed says the admin already exists | Expected; seed is idempotent | Nothing to do |
| Seed fails with a message about credentials | `ADMIN_EMAIL` / `ADMIN_PASSWORD` missing | Set them in `backend/.env` |
| Login fails after a password change elsewhere | Old session or wrong account | Sign out and sign in again |
| `401` / `403` from the API in the browser | Session expired, or `APP_ORIGIN` does not match the browser URL | Sign in again; check `APP_ORIGIN=http://localhost:3000` |
| `CSRF_TOKEN_INVALID` | Missing/mismatched CSRF cookie or header | Use the app; do not call the API from another origin |
| No slots for a date | No working window for that weekday, a break/override covers it, the date is beyond 30 days, it is inside the 2-hour notice, or the slot is held | Add a window, pick another date, or release the pending request |
| `409 USE_REJECT` | Trying to cancel a pending request as the provider | Use **Reject** |
| `403 CUTOFF_PASSED` | Customer action within 2 hours of the start | Pick a later appointment |
| `409 SLOT_UNAVAILABLE` | Someone else claimed the slot first | Refresh the slot list and choose another |
| Admin cannot confirm or reschedule | By design (D-009) | Ask the provider or customer |
| Port 3000 or 8000 already in use | Another dev server is running | Stop it, or use `next dev -p 3001` and update `APP_ORIGIN` |
| `npm run build` fails after dependency changes | Stale Next.js cache | `rm -rf .next && npm run build` |
| Tests fail to connect | Test database missing | `docker compose exec db createdb -U abs appointment_booking_test` |

---

## What to say about scope

Stating these up front prevents “why doesn't it…?” questions:

- No payments, email notifications, waitlists or provider self-registration.
- No background worker: pending expiry and time-based rules are applied lazily when the relevant
  operation runs.
- Completion is never automatic; a provider records it.
- Times are shown in the provider's timezone with a label; customer-timezone conversion is out of
  scope.
- Administrators may cancel appointments but cannot confirm, reject, complete or reschedule them.
- Accounts are deactivated, never hard-deleted, so history is preserved.
- The duration-equals-step grid can leave up to `duration − 1` minutes unused at the end of a
  window.
- A static Python type checker is not configured; Pydantic, SQLAlchemy, Ruff and the automated test
  suite are the safety net.

---

## If they want to run it themselves

Share the repository folder, or commit and push it first if you are sharing via Git. Then send them:

1. [`README.md`](../README.md) — prerequisites, setup, architecture, limitations.
2. This guide — the demo script and test commands.
3. `backend/.env.example` — they copy it to `.env`; the defaults work locally.
4. The seed credentials from `backend/.env` (change them in any shared environment).
5. [`docs/screenshots/`](screenshots/) — 13 static images if they want slides without a live demo.

Their first run is the same five steps as [Before the demo](#1-before-the-demo): database, migrate,
seed, API, web app. They create their own provider and customer accounts through the UI.

### Teardown

```bash
# stop the dev servers with Ctrl+C, then either:
docker compose stop db     # keep the data
# or
docker compose down        # remove the container; the abs_pgdata volume is kept
```

To delete the data as well: `docker compose down -v`.
