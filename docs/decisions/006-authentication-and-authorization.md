# 006 — Authentication, Authorization and CSRF

| | |
|---|---|
| **Decision ID** | D-006 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.A (registration, login, logout, profile, role-based access, protected pages), 5 (appropriate authentication and authorization) |
| **Scope additions** | `[T]` JWT in an `HttpOnly` cookie, same-origin proxy, layered CSRF defense |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The brief requires protected pages and role-based access but does not prescribe a mechanism. Two failure modes are easy to ship accidentally:

1. **Client-side-only protection** — hiding a link is not authorization.
2. **Cookie-based auth without CSRF defense** — cookies are attached automatically, so any site can cause authenticated state changes unless the request is verified.

A third constraint shaped the transport decision: the frontend and API are separate services. If the browser calls FastAPI cross-origin, cookies require `SameSite=None; Secure`, CORS with credentials, and careful preflight handling. Routing through Next.js keeps everything same-origin and removes that complexity.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-AUTH-1 | Registration |
| R-AUTH-2 | Login and logout |
| R-AUTH-3 | Profile management |
| R-AUTH-4 / 5 | Three roles, role-based access |
| R-AUTH-6 | Server-side protection, not UI hiding |
| R-TECH-7 | Authentication and authorization implemented |
| R-TECH-8 | Correct frontend/backend integration |

---

## 3. Options considered

### 3.1 Token transport

| Option | Risk |
|---|---|
| Bearer token in `localStorage` | Readable by any injected script; XSS becomes full account takeover |
| Bearer token in memory | Better, but lost on refresh and awkward with server rendering |
| `HttpOnly` cookie, cross-origin | Requires `SameSite=None; Secure`, credentialed CORS; fragile in local development |
| **`HttpOnly` cookie, same-origin via proxy (selected)** | Needs a proxy hop; no CORS credential handling |

### 3.2 Identity provider

| Option | Consequence |
|---|---|
| **FastAPI issues and validates JWTs (selected)** | One authority; Next.js stays a client |
| NextAuth as identity provider | Two authorities split across services; role claims must be synchronized |
| Session table with server-side sessions | Also valid; adds a session store and lookup per request |

### 3.3 CSRF defense

| Option | Coverage |
|---|---|
| `SameSite=Lax` alone | Incomplete: legacy browsers, same-site subdomain scenarios, misconfiguration |
| Origin/`Referer` validation alone | Strong for standard browsers; weak where the header is absent or stripped |
| **Origin validation + double-submit token + custom header + cookie attributes (selected)** | Layered; each layer covers a different failure |

---

## 4. Selected approach

### 4.1 Session transport

- FastAPI issues a signed JWT on successful login.
- The token is set in a cookie: `HttpOnly`, `Secure` (production), `SameSite=Lax`, `Path=/`, `__Host-` prefix in production.
- Browser traffic is same-origin: Next.js `rewrites` forwards `/api/*` to FastAPI.
- No wildcard CORS. Credentials are permitted only for the application's own origin in development.
- Next.js middleware performs **UX redirects only**; it is not an authorization boundary.
- Logout is a `POST` that clears the cookie.

### 4.2 Authorization

Every endpoint declares its required role and, where relevant, its ownership rule. The check runs in FastAPI after authentication and before any service call.

| Resource | Customer | Provider | Admin |
|---|---|---|---|
| Own profile | read/update | read/update | read/update |
| Provider profile | read | read/update own | create/update/deactivate any |
| Services | read | manage own | read |
| Availability | read | manage own | read |
| Appointments | own only | own provider's only | read all, cancel only |
| Users | self | self | list, deactivate |

Deactivated accounts fail authentication. Their records and history remain intact (D-001, D-009).

### 4.3 CSRF defense — four layers

`SameSite=Lax` is explicitly **not** treated as a complete defense.

| Layer | Mechanism | Failure response |
|---|---|---|
| **1. Origin validation** | Every state-changing request (`POST`/`PUT`/`PATCH`/`DELETE`) must carry `Origin` (fallback `Referer`) matching the configured `APP_ORIGIN`. Applies to `login` and `register` too, since they are state-changing. | `403 CSRF_ORIGIN_MISMATCH` |
| **2. Double-submit token** | Server issues a random 256-bit `csrf_token` in a **non-`HttpOnly`**, `SameSite=Lax` cookie. Client echoes it in `X-CSRF-Token`. Server compares header to cookie using a constant-time comparison. Stateless; no server-side store. | `403 CSRF_TOKEN_INVALID` |
| **3. Custom header requirement** | Because the token travels in a custom header, a classic cross-origin HTML form post cannot satisfy the check — forms cannot set headers. | Covered by layer 2 |
| **4. Cookie attributes** | `SameSite=Lax` plus `__Host-` prefix as defence in depth. | — |

Operational rules:

- The token is regenerated on login and on logout.
- `GET`, `HEAD` and `OPTIONS` are exempt.
- The check is a FastAPI dependency applied to every unsafe-method router and documented in the OpenAPI description.
- The frontend implements the header in one HTTP wrapper, so no call site can forget it.

```
Browser                     Next.js (same origin)              FastAPI
  |  POST /api/appointments        |                               |
  |  Cookie: __Host-session=...    |  forward unchanged            |
  |  Cookie: csrf_token=...        |                               |
  |  X-CSRF-Token: <echo>          |                               |
  |------------------------------->|------------------------------>|
  |                                |  1 Origin == APP_ORIGIN ?     |
  |                                |  2 header == cookie ?         |
  |                                |  3 JWT valid ?                |
  |                                |  4 role + ownership ?         |
  |<-------------------------------|<------------------------------|
```

### 4.4 Password handling

`[P]` Argon2id hashing, minimum 8 characters (U6). Login errors do not reveal whether an email exists.

---

## 5. Reasons

- A single authorization authority avoids the "two sources of truth" problem inherent in pairing NextAuth with a separate API.
- Same-origin routing makes `HttpOnly` cookies viable, which is strictly better than exposing a token to JavaScript.
- CSRF is a real risk for cookie-auth APIs; four independent layers mean no single browser quirk or misconfiguration removes protection.
- Origin validation also protects unauthenticated endpoints, which a token-only scheme cannot.
- A stateless double-submit token avoids a server-side token store while remaining effective.

---

## 6. Advantages and disadvantages

### Advantages

- Tokens are unreadable from JavaScript.
- No credentialed CORS configuration on the critical path.
- Authorization is centralized and testable as a matrix.
- CSRF protection costs one header in one wrapper.
- Deactivation takes effect immediately at the next authenticated request.

### Disadvantages

- The proxy hop adds a component to run and document.
- The frontend must read a non-`HttpOnly` cookie, which means the CSRF token is visible to scripts by design — acceptable, since it is not a credential alone.
- Stateless JWTs cannot be revoked individually before expiry; deactivation is checked per request, but a stolen token remains valid until expiry (U1).
- `Secure` cookies require HTTPS, so local development needs a documented exception.

---

## 7. Implications

**Security.** Authorization is server-side and deny-by-default. Origin validation plus double-submit addresses CSRF without relying on `SameSite` alone. Password hashes never leave the database layer. No secrets in logs.

**Data integrity.** The acting user is always taken from the verified token, never from the request body. `appointment_events.actor_user_id` therefore reflects the real actor.

**Performance.** One JWT verification and one role check per request — negligible. No session lookup.

**Testing.** Authorization matrix tests across role × endpoint × ownership. CSRF tests: missing `Origin`, wrong `Origin`, missing token, mismatched token, correct pair, and safe-method exemption.

---

## 8. Consequences for architecture and future changes

- One HTTP wrapper on the frontend owns the CSRF header and error mapping.
- Middleware may redirect; it must never be the only guard.
- Logout must clear both cookies and rotate the CSRF token.
- Adding a second frontend origin would require revisiting `APP_ORIGIN` validation and cookie scope.
- Refresh tokens, if added later, would need rotation and revocation storage — deliberately out of scope.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| `localStorage` bearer tokens | XSS becomes account takeover |
| Cross-origin cookie with `SameSite=None` | Adds credentialed CORS and preflight complexity for no benefit |
| NextAuth as the identity provider | Splits authority; role claims must be synchronized across services |
| Frontend-only route protection | Fails R-AUTH-6 |
| `SameSite=Lax` as the only CSRF defense | Incomplete on legacy browsers and same-site scenarios |
| Origin validation as the only CSRF defense | Depends on a header that can be absent or stripped |
| Server-side session store | Valid, but adds storage and a lookup without a requirement |
| Stateless CSRF token in a JWT claim | Token must be readable by the client to be echoed; a cookie is simpler |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[T]` JWT in `HttpOnly`, `SameSite=Lax`, `__Host-` cookie in production | Accepted |
| `[T]` Same-origin proxy through Next.js `rewrites` | Accepted |
| `[T]` FastAPI is the only authorization authority | Accepted |
| `[T]` Four-layer CSRF defense | Accepted |
| `[P]` Password policy: min 8 characters, Argon2id | U6 |
| Session lifetime and refresh strategy | U1 — proposed: short-lived token, re-login on expiry, no refresh |
| Local development cookie settings (`Secure` off, HTTP) | Documented exception in the README |
