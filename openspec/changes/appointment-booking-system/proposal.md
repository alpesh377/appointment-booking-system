# Proposal

## Why

The repository contains only an approved decision baseline (`docs/decisions/`) and an empty OpenSpec project — there is no application yet. The assignment requires a working full-stack appointment booking system where customers book providers, providers manage availability and appointments, and admins oversee the platform. This change establishes that system, implementing the accepted decisions as the behavioural contract rather than re-deriving rules during implementation.

## What Changes

- Introduce a **Next.js + TypeScript** frontend and a **Python FastAPI** backend backed by **PostgreSQL**, with Alembic migrations and OpenAPI documentation.
- Implement **account and role management**: public customer registration, admin-created provider accounts, seeded administrator, profile management, soft deactivation, and server-enforced role/ownership authorization.
- Implement the **provider directory**: browsable provider listings, provider detail pages with services, search by provider name or service category, and admin-driven provider creation, update and deactivation.
- Implement **availability management**: multiple working windows per weekday, recurring and date-specific breaks, date overrides that replace the weekly schedule, and a slot engine whose step equals the selected service's duration, anchored at each working window start.
- Implement **booking**: slot selection, optional notes, pending requests that hold their slot, lazy expiry, and structurally guaranteed non-overlap.
- Implement the **appointment lifecycle**: confirm, reject, cancel, reschedule via linked successor appointments, completion after the scheduled end, immutable terminal states, and an append-only event history.
- Implement the **admin console**: totals, statistics, customer and provider account management, whole-platform appointment views with filters, and supervisory cancellation.
- Implement the **web experience**: the ten required pages, responsive layout, and explicit loading, validation, empty and error states.
- Enforce concurrency integrity with a per-provider transaction-scoped advisory lock protocol plus a PostgreSQL exclusion constraint as the final overlap safeguard.
- Handle timezones with a per-provider IANA zone, provider-local slot generation, `timestamptz` storage, and a documented DST policy.
- Deliver the submission artefacts: migrations, README, environment example file, API documentation and screenshots.

No existing capability is modified: this is the project's first change. Nothing is removed or renamed.

## Capabilities

### New Capabilities

- `identity-and-access`: account lifecycle, registration and authentication, the three roles, profile management, deactivation, server-enforced authorization, session transport and CSRF defence.
- `provider-directory`: provider listings and detail pages, services with their own duration and category, search, and administrative provider creation, update and deactivation.
- `availability`: weekly working windows, breaks, date overrides, the slot-generation rules, provider timezone handling, and the prospective-only behaviour of schedule edits.
- `appointment-booking`: booking a slot for a service, pending reservation of that slot, lazy expiry, and the guarantee that no two active appointments overlap for one provider.
- `appointment-lifecycle`: the seven statuses and every legal transition, customer cancellation and rescheduling, provider confirmation, rejection, cancellation and completion, terminal-state immutability, and appointment history.
- `admin-console`: platform totals and statistics, customer and provider account administration, cross-provider appointment visibility and filtering, and supervisory cancellation.
- `web-experience`: the ten required pages, responsive presentation, and consistent loading, validation, empty and error feedback across every data view.

### Modified Capabilities

None. No existing capability has its requirements changed; this is the initial capability set for the project.

## Impact

- **New code**: `backend/` (FastAPI application, models, services, repositories, Alembic migrations, tests) and `frontend/` (Next.js App Router, components, API client).
- **New infrastructure**: PostgreSQL with the `btree_gist` and `citext` extensions; local orchestration for the database plus both services.
- **APIs**: a new HTTP API under `/api/*`, proxied same-origin through Next.js, documented via OpenAPI at `/docs`.
- **Dependencies**: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query; FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, `zoneinfo`, Argon2id hashing, pytest.
- **Documentation**: README, `.env.example`, API documentation, screenshots. The accepted decisions in `docs/decisions/` remain the rationale of record.
- **No migrations of existing data**: the database starts empty.

## Traceability

- Assignment requirements and acceptance criteria: `docs/decisions/requirements-and-scope.md` (§1), with stable `R-*` identifiers.
- Business-rule assumptions (`A1`–`A11`) are ours, not the brief's. Where a requirement derives from one, the spec names the assumption identifier so the distinction survives into implementation.
- Technical and submission requirements are constraints on implementation; they are carried by `design.md` and `tasks.md` rather than restated as behavioural deltas.
