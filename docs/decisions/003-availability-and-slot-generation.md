# 003 — Availability and Slot Generation

| | |
|---|---|
| **Decision ID** | D-003 |
| **Status** | Accepted |
| **Date decided** | 2026-10-23 |
| **Assignment requirements** | `[R]` 3.B (display availability and duration), 3.C (working days/hours, breaks, unavailable dates, slot display, availability updates), 3.D (date and time selection, no unavailable slots), 3.F / 3.G (date filtering) |
| **Scope additions** | `[P]` duration-equals-step grid anchored at window start, 30-day horizon, 2-hour notice, prospective-only edits, today-onward edit validation, multiple windows per weekday |
| **Supersedes** | — |
| **Superseded by** | — |

---

## 1. Context

Three inputs must compose into one answer: a provider's recurring working hours, their breaks, and date-specific exceptions. The output is a list of start times a customer may book for a specific service.

Two questions had to be answered that the brief leaves open: how free time becomes discrete start times, and what happens to existing appointments when availability later changes.

```
   weekly rules        breaks            date overrides
   Mon 09:00-17:00     Mon 12:00-13:00   2026-11-03 closed
   Tue 09:00-17:00     Tue 12:00-13:00   2026-11-10 10:00-14:00
   Wed 09:00-12:00
         |                  |                   |
         +---------+--------+---------+---------+
                   v
        [ effective windows for date D ]   override REPLACES weekly
                   v
        subtract breaks, then active appointments
                   v
        discretise by service duration, anchored at window start
                   v
        apply horizon and notice filters
                   v
        [ bookable slots for (provider, service, date) ]
```

---

## 2. Related assignment requirements

| ID | Bearing on this decision |
|---|---|
| R-AVL-1 | Configure working days and hours |
| R-AVL-2 | Define breaks |
| R-AVL-3 | Mark specific dates unavailable |
| R-AVL-4 | Display bookable slots |
| R-AVL-5 | Update availability |
| R-AVL-6 | No booking outside effective availability |
| R-BOOK-2 | Only currently valid slots offered |
| R-PROV-7 | Availability and duration displayed together |

---

## 3. Options considered

### 3.1 Availability model

| Option | Shape | Verdict |
|---|---|---|
| A | One `start`/`end` pair per weekday | Cannot express split shifts or lunch gaps without abusing breaks |
| B | Multiple windows per weekday + separate breaks + date overrides (selected) | Matches the brief's three explicit layers |
| C | Arbitrary calendar slots generated in advance | Requires a scheduler and stale-row management |

### 3.2 Slot grid

| Option | Rule | Consequence |
|---|---|---|
| A | Step equals duration, anchored at window start (selected) | Slots tile exactly; no intra-service overlap; small unused tail |
| B | Fixed 15/30-minute step, independent of duration | Better utilisation; more slots; overlapping candidate grid |
| C | Provider-configurable step | Adds a setting, per-provider variance, larger test matrix |
| D | Any minute | Absurd |

### 3.3 Availability edits vs existing appointments

| Option | Rule | Consequence |
|---|---|---|
| A | Prospective only; existing appointments untouched; conflicts surfaced (selected) | Schedule editing stays cheap; requires visibility |
| B | Block edits that would conflict | Couples two independent mechanisms; forces cancel-then-edit |
| C | Auto-cancel conflicting appointments | Destructive without consent |

---

## 4. Selected approach

### 4.1 Data model

- `availability_rules(provider_id, weekday 0-6, start_time, end_time)` — multiple rows per weekday allowed.
- `schedule_breaks(provider_id, weekday OR on_date, start_time, end_time)` — exactly one of `weekday` / `on_date` is set.
- `date_overrides(provider_id, date, is_closed)` with `date_override_windows(override_id, start_time, end_time)`.

### 4.2 Composition rules

1. A date override **replaces** that day's weekly schedule. A closed override produces no windows at all.
2. Breaks subtract from windows, whether weekly or date-specific.
3. Active appointments (`PENDING`, `CONFIRMED`) subtract from windows.
4. Everything else is derived; no slots are stored.

### 4.3 Grid

```
for each date in range:
    if date outside [today, today + 30 days]: continue
    if closed override: continue
    windows = override windows, else weekly rules for weekday
    occupied = breaks for the weekday + breaks for the date + active appointments
    for each window:
        t = window.start                       # anchored at WINDOW start
        while t + duration <= window.end:
            if [t, t + duration] does not intersect occupied
               and t - now > 2 hours:
                emit t
            t += duration
```

Grid properties:

- Every emitted slot fits entirely inside effective working time.
- Slots for one service are exactly adjacent — no unbookable micro-gaps.
- Different services produce different grids; cross-service overlap is prevented by the database constraint (D-005), not by the grid.
- Anchoring at the window start keeps the grid stable when a booking is cancelled.

### 4.4 Policy constants

| Rule | Value | Label |
|---|---|---|
| Booking horizon | 30 days ahead | `[P]` A2 |
| Minimum notice | `starts_at − now > 2h`, strict | `[P]` A1 |
| Buffers between appointments | none | `[P]` excluded |
| Grid anchoring | start of each effective working window | `[P]` |
| Editable dates | today and future only | `[P]` A8 |

### 4.5 Edits are prospective only

Changing hours, breaks, overrides, service duration, or provider/service activation:

- never modifies an existing appointment,
- never cancels an appointment automatically,
- only affects slot generation from that point forward.

Appointments that fall outside the new availability are surfaced in a provider dashboard group for manual handling. That group is distinct from the "confirmed, past, awaiting completion" group.

---

## 5. Reasons

- The three-layer model maps one-to-one onto the brief's three explicit availability requirements.
- Duration-equals-step is the only grid where slot length, spacing and non-overlap are the same number, which makes the function short, deterministic and easy to test.
- Anchoring at the window start gives the provider a stable, predictable grid: cancelling an appointment restores the same start time rather than shifting the day.
- Prospective-only editing follows from a simple principle: **availability governs what may be booked next, never what was already booked.** Non-overlap is enforced separately and independently.
- Bounding the horizon keeps availability queries finite without inventing pagination for time.

---

## 6. Advantages and disadvantages

### Advantages

- One pure, side-effect-free function produces the whole slot list; it can be tested without a database.
- No slot table, no scheduler, no stale generated rows.
- Split shifts, lunch breaks and holidays all fall out of the same composition rules.
- Schedule editing never needs to consult existing bookings, keeping the write path simple.

### Disadvantages

- **Unused tail.** Because the grid is anchored at the window start, an arbitrary duration leaves idle minutes at the end of a window. A 50-minute service in a 09:00–12:00 window yields 09:00, 09:50, 10:40 and then drops 11:30, leaving 30 minutes unbookable.
- **Orphaned appointments are possible.** A provider can shrink hours or close a date that already has bookings. The system flags them; it does not prevent or repair them.
- **Cross-service interference is subtle.** Two services with different grids can fragment a day in ways a provider does not expect. The constraint prevents overlap, but not surprise.
- **Per-service queries.** Availability is meaningless without a `service_id`.

---

## 7. Implications

**Security.** Availability is public read data for active providers only; deactivated providers and services must return no slots. Editing availability requires ownership of that provider profile. Slot responses must never leak other customers' appointment details — only availability.

**Data integrity.** No stored slots means no staleness. Date overrides are unique per `(provider, date)`. Window times are validated `start < end`, and windows and breaks may not produce negative intervals. `[P]` Edits are rejected for dates before today.

**Performance.** Slot generation is O(days × windows × slots per window) and bounded by the 30-day horizon. It reads rules, breaks and a bounded set of appointments; it writes nothing except the lazy expiry sweep described in D-005.

**Testing.** Direct unit tests for: window/break composition, closed overrides, override windows replacing weekly rules, duration fitting, grid anchoring, the unused tail, horizon boundaries, the strict notice boundary, and empty results. DST cases belong to D-007 but exercise this same function.

---

## 8. Consequences for architecture and future changes

- `GET /providers/{id}/availability?service_id=&from=&to=` is the availability contract.
- The slot engine lives in a service module and receives all inputs (including "now") as arguments — no hidden clock, no database session.
- The dashboard's "outside current availability" indicator is a query over existing appointments against current rules, not a stored flag.
- Buffers could be added later by widening the occupied interval by a constant; the grid itself would not change.
- A different grid policy (fixed step) could be substituted inside the same function signature without touching callers.

---

## 9. Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| One window per weekday | Cannot express split shifts without reusing breaks as pseudo-gaps |
| Fixed 15/30-minute step | Multiplies the slot list and test surface and invents a granularity the brief never asks for |
| Provider-configurable step | Adds a setting, per-provider variance and a wider test matrix |
| Per-minute starts | Produces unusable slot lists |
| Materialised slot table | Requires a scheduler and introduces staleness |
| Blocking availability edits that conflict | Couples schedule editing to booking, forcing cancel-then-edit flows |
| Auto-cancelling conflicting appointments | Destructive without the customer's knowledge, and email is out of scope |
| Anchoring the grid at each free interval | Maximises utilisation but lets the grid shift as bookings arrive |
| Unlimited horizon | Makes availability queries unbounded |

---

## 10. Assumptions and unresolved questions

| Item | Status |
|---|---|
| `[P]` 30-day horizon | Accepted (A2) |
| `[P]` Strict 2-hour minimum notice | Accepted (A1) |
| `[P]` No buffers | Accepted |
| `[P]` Grid anchored at window start, step equals duration | Accepted |
| `[P]` Edits limited to today and future dates | Accepted (A8) |
| `[P]` Existing appointments are never modified by schedule edits | Accepted |
| Break granularity: weekly breaks and date-specific breaks share one table | Implementation detail |
| Default horizon and notice values are configurable in settings, not hardcoded | Proposed default |
