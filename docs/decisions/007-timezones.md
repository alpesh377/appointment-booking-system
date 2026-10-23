# 007 — Timezone Handling

| | |
|---|---|
| **Decision ID** | D-007 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.C (working hours), 3.D (date and slot selection), implicit correctness of displayed times |
| **Scope additions** | `[P]` per-provider IANA timezone, provider-local display, documented DST policy |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

The brief never mentions timezones. Availability is nonetheless expressed in **wall-clock** terms ("I work 9 to 5") while appointments are **instants**. Treating them as the same thing produces a bug that appears twice a year and is invisible in a one-timezone demo.

```
  NAIVE: store "09:00" as 09:00 UTC
     summer (UTC-4): the provider's real hours become 05:00-13:00
     winter (UTC-5): they become 04:00-12:00
     different error in each season, and neither matches the intent

  CORRECT: store "09:00" as a wall-clock time plus a zone
     for each date, resolve 09:00 America/New_York
       -> 13:00Z in summer, 14:00Z in winter
```

A second trap: computing a "day" by adding 24 hours. On DST transition days a local day is 23 or 25 hours long.

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-AVL-1 | Working hours must mean what the provider intends |
| R-AVL-4 | Slots shown must be bookable at the displayed time |
| R-BOOK-2 | Slot validity depends on correct instant resolution |
| R-PROVD-1 | "Today's appointments" requires correct local-day boundaries |
| R-CUST-4 / R-ADMIN-5 | Date filters must not drift across a DST boundary |

---

## 3. Options considered

| Option | Shape | Consequence |
|---|---|---|
| A | Single global operating timezone | Simplest; wrong as soon as a provider is elsewhere; still requires care for DST |
| B | Per-provider zone, per-customer display conversion | Most correct; large UI and test surface, customer zone detection, dual labels |
| C | **Per-provider zone, provider-local display (selected)** | Correct storage and generation; one label; no customer conversion |
| D | Store fixed UTC offsets | Silently wrong twice a year |

---

## 4. Selected approach

### 4.1 Storage

| Data | Type | Interpretation |
|---|---|---|
| `provider_profiles.timezone` | IANA string | e.g. `America/New_York` |
| `availability_rules.start_time` / `end_time` | `time` | Wall clock in the provider's zone |
| `schedule_breaks.start_time` / `end_time` | `time` | Wall clock in the provider's zone |
| `date_overrides.date` | `date` | Provider-local calendar date |
| `appointments.starts_at` / `ends_at` | `timestamptz` | Absolute instants |
| `users` / `providers` timestamps | `timestamptz` | Absolute instants |

No naive timestamps anywhere. No stored UTC offsets.

### 4.2 Resolution

Python `zoneinfo` resolves wall-clock times to instants per date:

```
window: 2026-03-09 09:00-17:00 America/New_York
   -> 13:00Z - 21:00Z   (EDT)
window: 2026-12-09 09:00-17:00 America/New_York
   -> 14:00Z - 22:00Z   (EST)
```

The grid then walks instants, and each emitted slot is stored as `timestamptz`.

### 4.3 Local-day boundaries

Day boundaries are computed by resolving local midnight in the provider's zone, never by adding 24 hours:

```
day_start = datetime.combine(date, time.min, tzinfo=ZoneInfo(provider.timezone))
day_end   = day_start + one calendar day, resolved locally
```

This matters for "today's appointments", provider dashboard grouping, and date filters.

### 4.4 DST policy `[P]` (A6)

| Situation | Policy |
|---|---|
| A candidate local time does not exist (spring forward) | Skip it |
| A candidate local time occurs twice (fall back) | Take the first occurrence (`fold=0`) |
| A window spans the transition | Resolve start and end independently; the interval may be 23 or 25 hours of wall clock |

The policy is deterministic and directly testable.

### 4.5 Display

All times are rendered in the **provider's** timezone with an explicit label, for example `10:00 (America/New_York)`. API responses include the provider's zone alongside each timestamp so the client never guesses.

### 4.6 Provider timezone changes

Changing the zone affects future availability generation only. Existing appointments are instants and do not move. The UI warns before saving.

---

## 5. Reasons

- Provider-local rules are the only representation that survives DST without drifting.
- `timestamptz` makes the exclusion constraint correct by construction — it compares instants, so timezones cannot create overlaps.
- Provider-local display removes an entire feature (customer zone conversion) that the brief never requests, while keeping storage correct if it is added later.
- An explicit DST policy turns an edge case into a documented, tested rule instead of an accident.

---

## 6. Advantages and disadvantages

### Advantages

- Correct across DST transitions in both directions.
- Historic appointments remain accurate even if the provider later moves.
- Cross-provider comparison is safe because everything is stored as instants.
- No customer-zone detection, no dual labels, no ambiguity UI.

### Disadvantages

- A customer travelling to another timezone sees the provider's local time and must read the label.
- The DST policy is our invention; a 09:00–10:00 window is unaffected, but unusual overnight hours interact with it.
- Day-boundary arithmetic is easier to get wrong than `+24h`, so it needs dedicated tests.
- Timezone changes by a provider can surprise customers with already-offered future slots.

---

## 7. Implications

**Security.** None directly. Date filters must be derived server-side from the authenticated actor's role scope, not from a client-supplied timezone string.

**Data integrity.** Instant storage plus `tstzrange` means the overlap constraint is timezone-independent. Wall-clock rules are validated `start < end`. Overrides are per provider-local date.

**Performance.** `zoneinfo` conversions are cached by the standard library; cost is negligible relative to a query. Indexes on `starts_at` remain usable because comparisons are instant-based.

**Testing.** Dedicated cases for spring-forward and fall-back days, a window spanning the transition, local-day length on transition days, a provider in a different zone from the server, and a timezone change that must not move existing appointments.

---

## 8. Consequences for architecture and future changes

- Every timestamp crossing the API boundary is ISO 8601 with an offset; the provider's zone travels alongside.
- The frontend formats in the provider's zone and always shows the label.
- Adding customer-zone display later is a rendering change; no migration is required.
- A single-timezone deployment can set every provider to the same zone without code changes.
- Schedulers, if ever introduced, must resolve days in provider-local terms.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| Single global timezone | Wrong for multi-zone providers and still DST-sensitive; hides the problem rather than solving it |
| Per-customer display conversion in v1 | Large UI and test surface with no requirement behind it |
| Fixed UTC offsets | Silently wrong across DST |
| Naive timestamps | Ambiguous by definition; the bug this decision prevents |
| Storing slots as local naive datetimes | Makes cross-provider queries and the overlap constraint unreliable |
| `pytz`-style normalization | `zoneinfo` is the modern standard library answer and avoids legacy APIs |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` Provider stores an IANA timezone; display is provider-local with a label | Accepted |
| `[P]` DST policy: skip nonexistent, first occurrence for ambiguous (A6) | Accepted |
| `[P]` `zoneinfo` only; no fixed offsets, no naive timestamps | Accepted |
| `[P]` Local-day boundaries via local midnight | Accepted |
| `[P]` Provider timezone change does not move existing appointments | Accepted |
| Customer-facing timezone conversion | Excluded |
