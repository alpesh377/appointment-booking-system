# Spec Delta

## Purpose

Covers creating an appointment against a provider's available time, the reservation a pending request places on that time, and the guarantee that no provider ever holds two active appointments over the same instant.

## ADDED Requirements

### Requirement: Customers book an available slot for a service

The system SHALL create an appointment when an authenticated Customer selects an active provider, one of that provider's active services, and an available start time. The customer MAY attach optional notes.

#### Scenario: Successful booking
- **WHEN** a customer submits a valid provider, service, start time and optional notes
- **THEN** an appointment is created in the Pending status and confirmed to the customer

#### Scenario: Notes are optional
- **WHEN** a customer books without notes
- **THEN** the appointment is created successfully

#### Scenario: Notes are capped
- **WHEN** notes exceed the permitted length
- **THEN** the request is rejected with a validation error

### Requirement: Duration is derived from the service on the server

The system SHALL determine the appointment duration from the selected service at the moment of booking and MUST ignore any client-supplied end time or duration. The resolved start, end and duration SHALL be stored with the appointment and MUST NOT be recalculated from later service configuration.

#### Scenario: Client-supplied end time is ignored
- **WHEN** a booking request includes an end time inconsistent with the service duration
- **THEN** the stored interval uses the service duration

#### Scenario: Later duration change does not move history
- **WHEN** a provider changes a service's duration after appointments were booked
- **THEN** existing appointments retain their stored start, end and duration

### Requirement: Validation is repeated at booking time

The system SHALL re-validate at booking time that the provider and service are active, that the service belongs to the provider, that the start is inside effective availability, and that horizon and notice rules hold. A slot seen earlier MUST NOT be trusted.

#### Scenario: Service from another provider is rejected
- **WHEN** a booking names a provider and a service owned by a different provider
- **THEN** the booking is rejected

#### Scenario: Deactivated provider is rejected
- **WHEN** a booking targets a provider or service that has since been deactivated
- **THEN** the booking is rejected

#### Scenario: Stale slot is rejected
- **WHEN** a customer submits a slot that has ceased to be available
- **THEN** the booking is rejected and no appointment is created

### Requirement: A pending request reserves its slot

An appointment in the Pending status SHALL occupy its time slot for overlap purposes, so that no other appointment can be created over the same interval for that provider.

#### Scenario: Pending blocks a competing booking
- **WHEN** one customer holds a pending request for a start time
- **THEN** a second customer cannot book an overlapping interval

#### Scenario: Pending appears unavailable in availability results
- **WHEN** availability is computed while a pending request occupies part of a window
- **THEN** the occupied time is not offered

### Requirement: Pending requests expire and release their slot

A pending request SHALL expire at the earlier of 24 hours after creation and 2 hours before its start time. Expiry SHALL release the slot, set the appointment to Expired, and be recorded in history. Expiry SHALL be applied without any background worker. (Proposed assumption A3.)

#### Scenario: Expiry deadline is the earlier boundary
- **WHEN** a pending request is created more than 26 hours before its start
- **THEN** it expires 24 hours after creation

#### Scenario: Near-term request expires before its start
- **WHEN** a pending request is created close to its start time
- **THEN** it expires no later than 2 hours before the start

#### Scenario: Expired request frees the slot
- **WHEN** a pending request passes its expiry deadline and availability is next computed or a booking is attempted
- **THEN** the request becomes Expired and its slot becomes bookable

#### Scenario: Expiry is recorded
- **WHEN** a request expires
- **THEN** an event records the transition with the system as the actor

### Requirement: Active appointments can never overlap

The system SHALL reject any attempt that would leave one provider holding two appointments in Pending or Confirmed status whose intervals overlap. This guarantee MUST hold under concurrent requests and MUST be enforced independently of application-level checks.

#### Scenario: Concurrent requests for one slot
- **WHEN** two customers submit the same slot at the same time
- **THEN** exactly one booking succeeds and the other is rejected as unavailable

#### Scenario: Variable durations cannot slip past
- **WHEN** a 90-minute booking is submitted over time that a 30-minute grid treats as free
- **THEN** the overlap is detected and the booking is rejected

#### Scenario: Terminal statuses free the slot
- **WHEN** an appointment becomes Cancelled, Rejected, Expired, Completed or Rescheduled
- **THEN** its interval no longer blocks new bookings

### Requirement: Booking confirmation reports the appointment

The system SHALL present a confirmation containing the provider, service, start and end times with the provider's timezone label, the notes and the appointment status.

#### Scenario: Confirmation is shown after booking
- **WHEN** a booking succeeds
- **THEN** the confirmation page displays the provider, service, time and status

#### Scenario: Status is always visible
- **WHEN** an appointment is displayed anywhere in the interface
- **THEN** its current status is displayed with it
