# 002 — Provider Services and Duration

| | |
|---|---|
| **Decision ID** | D-002 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.B (provider profiles and service details, search by service category, display appointment duration), 3.D (book a provider's service), 3.C (availability per duration) |
| **Scope additions** | `[P]` duration bounds and granularity; category carried by the service rather than the provider |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The brief asks for "provider profiles and service details", search by "name or service category", and display of "appointment duration". It never says whether duration belongs to the provider or to the service, and it never says whether a provider offers one thing or many.

That ambiguity is structural, not cosmetic: the slot grid is generated from a duration, so the answer determines the entire availability algorithm.

```
  (a) duration on provider              (b) duration on service (selected)
  +----------------------+              +------------------------------+
  | Provider             |              | Provider                     |
  |   duration: 30 min   |              |   services:                  |
  |   category: Barber   |              |     Haircut     30 min       |
  +----------------------+              |     Colour      90 min       |
                                        +------------------------------+
  one grid per provider                 one grid per (provider, service)
  one bookable thing                    "service details" has content
```

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-PROV-2 | Provider detail page must show service details |
| R-PROV-3 | Search by service category |
| R-PROV-7 | Display availability and appointment duration |
| R-BOOK-1 | Booking starts from a provider |
| R-BOOK-2 | Only valid slots are offered |
| R-AVL-6 | No booking outside availability |

---

## 3. Options considered

### Option A — Duration on the provider only

One duration per provider; every appointment is that length. Simplest grid, but "service details" becomes a free-text field with no operational meaning.

### Option B — Duration on the service, many services per provider (selected)

A provider offers 1..N services. Each service has a name, a category and a duration. Booking selects a service; that service's duration drives the grid.

### Option C — Duration on both, provider default overridden per service

Adds a fallback value that is never used once services exist, and invites disagreement between the two fields.

### Option D — Price and duration on the service

Adds commercial data the brief never mentions.

---

## 4. Selected approach

1. `services(id, provider_id, name, category, duration_minutes, is_active, ...)`, 1..N per provider.
2. `duration_minutes` is validated to **15–480 minutes in multiples of 5** `[P]`.
3. **No provider-level duration field exists.** Provider listings summarise the durations of the provider's active services.
4. Category lives on the **service** `[P]`, so one provider can offer services in different categories; search matches either provider name or service category.
5. No price, currency or payment fields.
6. Availability is always computed for a specific `(provider, service, date)`.

---

## 5. Reasons

- "Service details" and "search by service category" only make sense if services are first-class entities.
- Different genuine services have different lengths. Forcing one duration per provider would make a 90-minute colouring and a 30-minute trim share a grid that fits neither.
- Putting category on the service lets search return a provider because of *what they offer*, which is what a customer is actually searching for.
- A single source for duration removes a whole class of "which value wins" bugs.

---

## 6. Advantages and disadvantages

### Advantages

- Provider pages have real, differentiated content.
- One service's duration change does not disturb another's availability.
- The grid remains a single, understandable rule per service.
- Search is meaningful at the service level.

### Disadvantages

- Availability is no longer a provider-level query; every availability call must carry a `service_id`.
- The booking API must resolve duration server-side from the service, never trust a client-supplied end time.
- Services add a management surface for the provider (a list to maintain).
- The 15–480 / multiple-of-5 bounds are our invention and will reject some real-world durations (for example a 20-minute consultation).

---

## 7. Implications

**Security.** Service ownership is checked on every booking and availability request: a service belonging to another provider must be rejected, otherwise a customer could book provider A's time using provider B's duration.

**Data integrity.** `services.provider_id` is a foreign key with restrictive delete; services are deactivated, never removed, because appointments reference them. `duration_minutes` carries a database `CHECK` in addition to schema validation.

**Performance.** One extra indexed join per availability query. Negligible.

**Testing.** Two services with different durations must produce different slot lists from the same window — a direct unit-test case in D-008. Duration bounds and non-multiple-of-5 rejection are validation cases.

---

## 8. Consequences for architecture and future changes

- The availability endpoint requires `service_id`; omitting it is a `422`.
- `appointments.service_id` is required, and `appointments.duration_minutes` snapshots the value used at booking time.
- Adding pricing later would extend `services` without disturbing the grid.
- If category ever becomes a taxonomy, it moves from free text to a lookup table; the search behaviour is unchanged.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| Option A — provider-level duration | Makes "service details" non-functional and forces every service to share one length. |
| Option C — provider default plus service override | Two sources of truth for one number, with a fallback path that is dead once services exist. |
| Option D — price on service | Not requested; introduces money handling and rounding questions. |
| A single global duration constant | Simplest of all, but contradicts the brief's mention of service details and duration as provider-visible information. |
| Free-text duration | Unparseable for grid generation. |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` Duration bounds 15–480 minutes, multiples of 5 | Accepted (A5) |
| `[P]` Category on the service, free text, case-insensitive search | Accepted; taxonomy vs free text tracked as U2 |
| `[P]` No provider-level duration field | Accepted |
| Service display name is resolved through the foreign key, not snapshotted. Renaming a service therefore changes how historical appointments display it. | Known limitation; no additional column was approved |
| Currency, price and payment | Excluded |
