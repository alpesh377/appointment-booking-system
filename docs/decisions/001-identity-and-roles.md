# 001 — Identity and Roles

| | |
|---|---|
| **Decision ID** | D-001 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.A (authentication, roles, protected pages), 3.B (admin creates/updates/deactivates providers), 3.H (admin manages customers and providers), 5 (authentication and authorization) |
| **Scope additions** | `[P]` single-role accounts, admin-seeded first administrator, no self-service provider onboarding |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The brief requires two things that pull in opposite directions:

- **3.A** — public "user registration and login", with three roles.
- **3.B / 3.H** — administrators "create, update, and deactivate provider profiles" and "manage customer accounts".

If registration lets a visitor choose "Service Provider", the administrator's provider-management power becomes decorative. If only administrators can create *any* account, public registration contradicts 3.A. The system needs an identity model that honours both without allowing privilege self-assignment.

A second question sits underneath: can one person be a customer and a provider at the same time?

```
   single role per account                 multi-role account
   +--------------------------+            +--------------------------+
   | user -> exactly one role |            | user -> {roles}          |
   | provider -> profile      |            | provider -> profile      |
   +--------------------------+            +--------------------------+
   simple authorization checks              "which dashboard?" question,
   one dashboard per person                 role switcher in the UI,
                                            ambiguous audit attribution
```

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-AUTH-1 | Registration must exist and must not grant provider access |
| R-AUTH-4 | Three distinguishable roles |
| R-AUTH-5 | Role determines access |
| R-PROV-4 | Admin creates providers |
| R-PROV-6 | Admin deactivates providers |
| R-ADMIN-2 | Admin manages customer accounts |
| R-ADMIN-3 | Admin creates, updates and deactivates provider accounts |

---

## 3. Options considered

### Option A — Admin-only provider creation (selected)

Public registration always produces a `Customer`. An administrator creates provider accounts and assigns an initial password. The first administrator is created by a documented seed/setup command, never a hardcoded credential.

### Option B — Self-register as provider with administrator approval

Registration offers a "I provide services" choice, creating a provider in `pending_approval`. An administrator approves or rejects.

### Option C — Self-register as provider, immediately active

Fastest onboarding, but removes the administrator's provider-management role entirely and lets anyone appear in the public catalogue.

### Option D — Separate identity systems per role

Distinct customer, provider and admin login flows with separate credential stores.

### Option E — Multi-role accounts

A user may hold several roles and switch context inside the application.

---

## 4. Selected approach

1. One `users` row per account with a single scalar `role` in `{admin, provider, customer}`.
2. Public registration creates `customer` only. The role is never read from the request body.
3. Provider accounts are created by an administrator, together with a `provider_profiles` row.
4. The first administrator is created by a documented seed/setup command using environment-supplied credentials. No default password ships in the repository.
5. `provider_profiles` is 1:1 with a provider user and is the anchor for services, availability and appointments.
6. Deactivation is soft: `users.is_active = false` and, for providers, `provider_profiles.is_active = false`. Nothing is deleted.

---

## 5. Reasons

- It satisfies both halves of the brief simultaneously. Registration exists (3.A) and provider management remains meaningful (3.B, 3.H).
- It removes privilege escalation by construction: there is no request shape in which a client asserts a role.
- Scalar roles keep every authorization check a single comparison, which makes the authorization matrix testable rather than combinatorial.
- A seed command keeps credentials out of source control while still producing a usable demo environment — a direct requirement of good submission hygiene.
- Soft deactivation preserves history, which 3.E and 3.F require (past and cancelled appointments must remain visible).

---

## 6. Advantages and disadvantages

### Advantages

- One login, one dashboard, one permission model.
- No approval workflow state to design, test or explain.
- Provider deactivation is a single flag with no cascading deletes.
- The admin can always be recreated from the seed command if credentials are lost.

### Disadvantages

- A person who both provides services and books them needs two accounts with two email addresses.
- No invite email: the administrator must communicate the initial password out of band.
- No forced password change on first login in this scope, so an initial password may persist. Recorded as a limitation, not a hidden behaviour.
- Administrator creation of providers is manual and does not scale to many providers — acceptable for the assignment's scope.

---

## 7. Implications

**Security.** Role is server-assigned and server-read. The only privilege boundary crossed at registration is "none". Provider accounts cannot be created by anyone but an administrator. Deactivated accounts are rejected at authentication, not merely hidden in the UI.

**Data integrity.** `provider_profiles.user_id` is unique, so a provider cannot accidentally acquire two profiles. Deactivation never removes rows, so appointment foreign keys remain valid forever.

**Performance.** Negligible. Role checks are a column read already loaded with the session.

**Testing.** The authorization matrix in D-008 exercises `(role × endpoint × ownership)`. This decision collapses the "which roles does this user have" dimension to a single value, which is why that matrix stays tractable.

---

## 8. Consequences for architecture and future changes

- `appointments.provider_id` references `provider_profiles.id`; `appointments.customer_id` references `users.id`. These are different tables by design.
- Every dashboard is scoped by role, not by a role set.
- Adding provider self-registration later would require a provider approval state and would not invalidate this model — it would add a state to `provider_profiles`.
- Supporting dual roles later would require replacing the scalar `role` with a join table and introducing a context switcher; that is a deliberate future migration, not an accident to be papered over.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| Option B — self-register with approval | Adds a provider state machine, notification requirement and approval UI, while making "admin creates providers" partly redundant. More surface for no required behaviour. |
| Option C — self-register, immediately active | Lets any visitor enter the public catalogue. Effectively deletes R-PROV-4 and R-ADMIN-3. |
| Option D — separate identity per role | Triples authentication code paths and makes "admin also needs to log in" awkward. No requirement justifies it. |
| Option E — multi-role accounts | Forces a role switcher, ambiguous audit attribution, and compound authorization checks. The brief never implies a user holds multiple roles. |
| Hardcoded admin credentials in a migration | Ships a known password in the repository. Rejected on security grounds. |
| Hard-deleting deactivated accounts | Destroys the appointment history the brief requires. |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` First administrator supplied through a documented seed/setup command with environment credentials | Accepted |
| `[P]` One role per account; no dual-role users | Accepted |
| Provider initial password is communicated out of band; no invite email | Out of scope (email excluded) |
| No forced password change on first login | Known limitation |
| Password policy (minimum length, hashing algorithm) | U6 — proposed default: minimum 8 characters, Argon2id |
| Administrative "edit provider" covers profile fields only | U8 — proposed default: name, category, contact, bio, activation |
