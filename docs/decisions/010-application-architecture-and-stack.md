# 010 — Application Architecture and Stack

| | |
|---|---|
| **Decision ID** | D-010 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 5 (Next.js + TypeScript, FastAPI, PostgreSQL, UI library, maintainable structure, correct integration), 4 (responsive UI with full state coverage), 6 (submission artefacts) |
| **Scope additions** | `[T]` specific libraries and module boundaries |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The assignment fixes the three technologies but not how they are organised. Two integrations are possible — the browser calling FastAPI directly, or the browser calling Next.js which proxies to FastAPI — and each implies a different story for cookies, CSRF and CORS (D-006).

The code also has to be readable by a reviewer. The failure mode for take-home projects is a flat structure where routers query the database directly, the slot algorithm lives inside an endpoint, and authorization checks are copy-pasted.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-TECH-1 | Next.js with TypeScript |
| R-TECH-2 | Python FastAPI |
| R-TECH-3 | PostgreSQL |
| R-TECH-4 | Swagger / OpenAPI |
| R-TECH-5 | UI library or CSS framework |
| R-TECH-6 | Clear, maintainable organisation |
| R-TECH-8 | Correct integration |
| R-UI-1..5 | Responsive layout and full state coverage |
| R-SUB-1..7 | Source, migrations, README, env example, API docs, screenshots |

---

## 3. Options considered

| Area | Options | Chosen |
|---|---|---|
| Integration | Direct cross-origin API calls; **same-origin proxy through Next.js** | Proxy |
| Rendering | Pure SPA; **App Router with Server Components for the shell** | App Router |
| Styling | Hand-written CSS; CSS modules; **Tailwind + shadcn/ui** | Tailwind + shadcn/ui |
| Client data | Manual `fetch` + `useEffect`; **TanStack Query** | TanStack Query |
| Form state | Manual `useState` per field; **React Hook Form + Zod** | React Hook Form + Zod |
| Backend structure | Routers query the ORM directly; **routers → services → repositories** | Layered |
| ORM | Raw SQL; SQLAlchemy 2.0 | SQLAlchemy 2.0 |
| Migrations | Hand-maintained SQL; **Alembic** | Alembic |
| Test database | SQLite; **real PostgreSQL** | PostgreSQL |

---

## 4. Selected approach

### 4.1 Frontend

- **Next.js App Router + TypeScript.**
- **Server Components** render the application shell and layout; **Client Components** own forms, filters and slot pickers.
- **TanStack Query** for client-side fetching and mutations, giving uniform loading, empty and error states.
- **React Hook Form + Zod** for form state and validation. Schemas mirror the FastAPI request models,
  and server-side field errors are mapped back onto the offending fields.
- **Tailwind CSS v4 + shadcn/ui** for responsive layout and accessible primitives. Theme tokens
  live in `globals.css` under `@theme inline`; there is no JavaScript Tailwind config.
- **Motion** for short, reduced-motion-aware transitions only; no global client store is used because
  authentication state lives in a React context and server state belongs to TanStack Query.
- One HTTP wrapper attaches the CSRF header and maps `401`/`403`/`409`/`422` to consistent UI messages.
- Every data view implements loading, empty and error states explicitly (R-UI-2, R-UI-4, R-UI-5).

### 4.2 Backend

- **FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic.**
- Layering:
  - **Routers** — HTTP surface, status codes, OpenAPI metadata.
  - **Dependencies** — authentication, role and ownership checks, CSRF validation.
  - **Services** — slot engine, booking, lifecycle, reschedule, admin supervision.
  - **Repositories** — queries, transaction boundaries, lock acquisition.
- The slot engine is a **pure function** with no I/O and no implicit clock.
- Errors use stable machine-readable codes (`SLOT_UNAVAILABLE`, `USE_REJECT`, `CSRF_TOKEN_INVALID`, …) alongside human messages.

### 4.3 Database

- **PostgreSQL** with `btree_gist`, `citext`, `timestamptz` and an exclusion constraint.
- Alembic owns the schema; the first migration enables `btree_gist`.
- Status stored as constrained `VARCHAR` rather than a native enum, so migrations remain simple.

### 4.4 Request flow

```
  Browser
     |  same-origin fetch, CSRF header, HttpOnly cookie
     v
  Next.js (App Router)  --- rewrites /api/* --->  FastAPI
     |  Server Components render the shell          |
     |  TanStack Query fetches data                 |  routers -> services -> repositories
     |  middleware = UX redirects only              v
     |                                        PostgreSQL
     +---------------- no direct DB access -----+
```

### 4.5 Directory shape

```
backend/
  app/
    api/            routers by role and resource
    core/           config, security, csrf, errors, logging
    models/         SQLAlchemy models
    schemas/        Pydantic models
    services/       availability, booking, lifecycle, admin
    repositories/   queries and transaction helpers
  alembic/
  tests/
frontend/
  app/              routes by role
  components/       shared UI + shadcn primitives
  lib/              api client, formatting, auth helpers
  hooks/            TanStack Query hooks
docs/decisions/
```

---

## 5. Reasons

- The same-origin proxy is what makes `HttpOnly` cookies and layered CSRF practical; direct cross-origin calls would force `SameSite=None` and credentialed CORS.
- App Router with Server Components gives fast first paint and a clean role-based layout without a separate SPA shell.
- shadcn/ui provides accessible primitives that can be themed rather than a rigid design system, which is the fastest route to a credible UI.
- TanStack Query removes the boilerplate of loading and error states while making them consistent.
- The layered backend is the difference between "it works" and "someone else can extend it", which is explicitly graded.
- A pure slot engine is what makes category 1 of D-008 writable at all.

---

## 6. Advantages and disadvantages

### Advantages

- One origin, no credentialed CORS, simple cookie story.
- Consistent loading, empty and error handling across every page.
- The slot engine and lifecycle rules are testable without HTTP or a database session.
- Alembic provides a reviewable schema history.
- Conventional choices reduce reviewer friction.

### Disadvantages

- Two services to run, document and keep in sync.
- The proxy adds a hop and one more place for configuration errors.
- TanStack Query is a dependency that must be used consistently; mixing it with ad-hoc `fetch` would fragment error handling.
- shadcn/ui means generated components live in the repository and must be maintained.
- Server Components plus client querying requires a deliberate boundary; blurring it causes hydration surprises.

---

## 7. Implications

**Security.** The frontend holds no authority. FastAPI enforces every rule. The HTTP wrapper is the single place where CSRF and auth failures are handled.

**Data integrity.** Repositories own transactions and locks, so the D-005 protocol cannot be accidentally split across layers. Alembic makes schema changes reviewable.

**Performance.** Server Components reduce client JavaScript; slot queries are bounded by the 30-day horizon; list endpoints are paginated.

**Testing.** Services are unit-testable; repositories are integration-tested against real PostgreSQL; routers are covered by the authorization matrix and CSRF cases.

---

## 8. Consequences for architecture and future changes

- Adding an endpoint means: schema → repository → service → router → authorization entry in the matrix → frontend hook.
- The proxy configuration (`APP_ORIGIN`, rewrite target) is the single point of integration failure and must be documented in the README.
- A future mobile client could call FastAPI directly, but would need its own auth transport decision.
- Replacing shadcn/ui would be a component-level change, not an architectural one.
- If the frontend ever needs server-side authorization decisions, they must still be re-verified by FastAPI.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| Direct cross-origin browser → FastAPI | Forces `SameSite=None; Secure`, credentialed CORS and preflight handling |
| Pure client-side SPA | Slower first paint, more client state, no benefit here |
| Tokens in `localStorage` | XSS exposure (D-006) |
| Hand-written CSS | Slower to a responsive, accessible result |
| Manual `fetch` + `useEffect` everywhere | Duplicated loading and error logic, inconsistent states |
| Routers querying the ORM directly | Couples HTTP to persistence; makes the slot engine untestable |
| Raw SQL instead of SQLAlchemy | More code, weaker typing, no migration story |
| Hand-written migrations | Not reviewable; R-SUB-2 expects migration files |
| SQLite for development | Cannot exercise constraints the system depends on |
| A single combined server | Would violate R-TECH-1/R-TECH-2 and the explicit two-service requirement |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[T]` Same-origin proxy through Next.js `rewrites` | Accepted |
| `[T]` Tailwind + shadcn/ui | Accepted |
| `[T]` TanStack Query + Server Components | Accepted |
| `[T]` routers → services → repositories | Accepted |
| `[T]` SQLAlchemy 2.0 + Alembic + Pydantic v2 | Accepted |
| Deployment target and local topology | U5 — proposed: `docker-compose` for Postgres plus both services |
| Pagination defaults | U4 — proposed: 20 per page |
| Service category storage | U2 — proposed: free text with suggestions |
| Seed data volume | U7 — proposed: small curated fixture set |
| Screenshots workflow | U9 — proposed: manual capture during the final run |
