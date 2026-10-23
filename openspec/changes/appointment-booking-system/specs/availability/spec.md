# Spec Delta

## Purpose

Defines when a provider is available, how that availability is expressed across working hours, breaks and date exceptions, and how bookable start times are derived for a specific service.

## ADDED Requirements

### Requirement: Providers configure multiple working windows per weekday

The system SHALL allow a provider to define one or more working windows for each weekday, each with a start and end time in the provider's local time. Windows for the same weekday MUST NOT overlap.

#### Scenario: Split shift is configured
- **WHEN** a provider defines Monday 09:00-12:00 and Monday 13:00-17:00
- **THEN** both windows are retained and contribute to availability

#### Scenario: Overlapping windows are rejected
- **WHEN** a provider submits two windows for the same weekday that overlap
- **THEN** the request is rejected with a validation error

### Requirement: Breaks are excluded from availability

The system SHALL allow a provider to define break periods that recur on a weekday and break periods that apply to one specific date. A break MUST remove the covered time from effective availability.

#### Scenario: Recurring break removes time every week
- **WHEN** a provider defines a 12:00-13:00 break on Mondays
- **THEN** no Monday slot overlaps that period

#### Scenario: Date-specific break removes time once
- **WHEN** a provider defines a break for one date only
- **THEN** only that date is affected

### Requirement: Date overrides replace the weekly schedule

The system SHALL allow a provider to define an override for a specific date. An open override SHALL replace that date's weekly windows with its own windows; a closed override SHALL produce no availability for that date.

#### Scenario: Closed date produces no slots
- **WHEN** a provider marks a date as closed
- **THEN** no slots are offered for that date, even if the weekday normally has working windows

#### Scenario: Override hours replace weekly hours
- **WHEN** a provider sets a 10:00-14:00 override on a date that normally runs 09:00-17:00
- **THEN** only 10:00-14:00 contributes to availability on that date

#### Scenario: Only one override exists per date
- **WHEN** a provider submits a second override for a date that already has one
- **THEN** the request is rejected or replaces the existing override rather than creating a duplicate

### Requirement: Availability is determined per provider, service and date

The system SHALL compute availability for one provider, one service and one date or date range. Availability requests that omit the service MUST be rejected, because the duration depends on the service.

#### Scenario: Different services yield different slots
- **WHEN** one provider offers a 30-minute service and a 90-minute service in the same 09:00-12:00 window
- **THEN** each service produces its own slot list for that day

#### Scenario: Service is required
- **WHEN** a client requests availability without identifying a service
- **THEN** the request is rejected with a validation error

#### Scenario: Service must belong to the provider
- **WHEN** a client requests availability using a service owned by a different provider
- **THEN** the request is rejected

### Requirement: Slots follow the anchored duration grid

The system SHALL generate candidate start times at the start of each effective working window and at successive multiples of the service duration. A slot SHALL be offered only when the entire service duration fits inside effective availability after breaks and active appointments are removed.

#### Scenario: Slots tile from the window start
- **WHEN** a 30-minute service is offered in a 09:00-12:00 window without breaks
- **THEN** the offered starts are 09:00, 09:30, 10:00, 10:30, 11:00 and 11:30

#### Scenario: A slot may not straddle a break
- **WHEN** a candidate slot would overlap a break or extend beyond the window
- **THEN** that candidate is not offered

#### Scenario: Tail time may remain unused
- **WHEN** the remaining time before a window end is shorter than the service duration
- **THEN** no additional slot is offered and the unused remainder is accepted

#### Scenario: Active appointments remove slots
- **WHEN** an appointment already occupies part of a window
- **THEN** no slot overlapping it is offered

### Requirement: Availability is bounded by horizon and notice

The system SHALL offer slots only within 30 days of the current moment and only where the start is strictly more than 2 hours in the future. (Proposed assumptions A1 and A2.)

#### Scenario: Slot beyond the horizon is not offered
- **WHEN** a date falls more than 30 days ahead
- **THEN** it produces no slots

#### Scenario: Slot inside the notice period is not offered
- **WHEN** a slot would start 2 hours or fewer from now
- **THEN** it is not offered

#### Scenario: Boundary is exclusive
- **WHEN** a slot would start exactly 2 hours from now
- **THEN** it is not offered

### Requirement: No appointment is created outside effective availability

The system SHALL reject any booking whose interval is not fully inside effective availability for that provider, service and date.

#### Scenario: Booking a break is rejected
- **WHEN** a customer submits a start time that falls inside a break
- **THEN** the booking is rejected and no appointment is created

#### Scenario: Booking a closed date is rejected
- **WHEN** a customer submits a start time on a closed date
- **THEN** the booking is rejected

### Requirement: Providers edit their own availability

The system SHALL allow a Service Provider to view and change their own working windows, breaks and date overrides. A provider MUST NOT change another provider's availability, and an Administrator MUST NOT change any provider's availability.

#### Scenario: Provider edits working hours
- **WHEN** a provider submits a valid change to their working windows
- **THEN** the change is stored and affects subsequent slot generation

#### Scenario: Unauthorized availability edit is refused
- **WHEN** a provider targets another provider's availability, or an Administrator targets any provider's availability
- **THEN** the request is rejected as forbidden

### Requirement: Availability edits apply only to today and future dates

The system SHALL reject availability changes that target a date before today. (Proposed assumption A8.)

#### Scenario: Past date is refused
- **WHEN** a provider attempts to create or change availability for a past date
- **THEN** the request is rejected with a validation error

### Requirement: Schedule edits never modify existing appointments

Changing working windows, breaks, date overrides, service duration or activation MUST NOT modify, move or cancel any existing appointment. Affected appointments SHALL be surfaced to the provider for manual handling.

#### Scenario: Shortening hours strands nothing
- **WHEN** a provider shortens a working window so that an existing appointment falls outside it
- **THEN** the appointment keeps its original time and status

#### Scenario: Affected appointments are surfaced
- **WHEN** existing appointments fall outside the provider's current availability
- **THEN** the provider dashboard identifies them separately from appointments awaiting completion

#### Scenario: Closed date with bookings
- **WHEN** a provider marks a date closed that already has appointments
- **THEN** the closure is accepted, the appointments remain unchanged and they are identified for manual handling

### Requirement: Availability respects the provider timezone

The system SHALL store each provider's IANA timezone and interpret working windows, breaks and overrides as wall-clock times in that zone. Appointment instants SHALL be stored unambiguously and displayed in the provider's timezone with an explicit label.

#### Scenario: Same rule across daylight-saving change
- **WHEN** a provider works 09:00-17:00 across a daylight-saving transition
- **THEN** the local hours remain 09:00-17:00 and the underlying instants shift by the zone's offset change

#### Scenario: Nonexistent local time is skipped
- **WHEN** a candidate local time does not exist on a spring-forward day
- **THEN** that candidate is not offered

#### Scenario: Ambiguous local time uses the first occurrence
- **WHEN** a candidate local time occurs twice on a fall-back day
- **THEN** the first occurrence is used

#### Scenario: Display carries a zone label
- **WHEN** a time is presented to a user
- **THEN** it is shown in the provider's timezone with that timezone identified

### Requirement: Provider timezone changes affect only future availability

The system SHALL warn before a provider changes their timezone. A timezone change MUST NOT move existing appointment instants and SHALL affect only availability generated afterwards.

#### Scenario: Existing appointments do not move
- **WHEN** a provider changes their timezone
- **THEN** existing appointments retain their original instants

#### Scenario: Warning is presented
- **WHEN** a provider initiates a timezone change
- **THEN** the interface warns that future availability will be reinterpreted
