# Spec Delta

## Purpose

Defines the states an appointment can occupy, who may move it between them, how cancellation and rescheduling behave, how completion is recorded, and how customers and providers see their appointment lists.

## ADDED Requirements

### Requirement: Appointments use a closed set of seven statuses

Every appointment SHALL be in exactly one of: Pending, Confirmed, Rejected, Cancelled, Completed, Expired or Rescheduled. Rejected, Cancelled, Completed, Expired and Rescheduled SHALL be terminal and MUST NOT change to any other status.

#### Scenario: Terminal status is immutable for every role
- **WHEN** any user, including an Administrator, attempts to change a terminal appointment to another status
- **THEN** the request is rejected and the status is unchanged

#### Scenario: Status is exposed wherever an appointment appears
- **WHEN** an appointment is listed or opened
- **THEN** its status is part of the displayed data

### Requirement: Providers confirm or reject pending requests

The system SHALL allow the provider who owns a pending request to confirm it or reject it. No other role and no other provider may do so.

#### Scenario: Provider confirms
- **WHEN** the owning provider confirms a pending request
- **THEN** the appointment becomes Confirmed and its slot remains reserved

#### Scenario: Provider rejects
- **WHEN** the owning provider rejects a pending request
- **THEN** the appointment becomes Rejected and its slot is released

#### Scenario: Another provider attempts to act
- **WHEN** a provider confirms or rejects an appointment belonging to a different provider
- **THEN** the request is rejected as forbidden

### Requirement: Providers must reject rather than cancel a pending request

A Service Provider MUST NOT cancel an appointment in the Pending status. Such an attempt SHALL be refused with a conflict indicating that rejection is the correct action. (Proposed rule.)

#### Scenario: Cancelling a pending request as a provider
- **WHEN** a provider attempts to cancel a pending request
- **THEN** the request is rejected with a conflict and the appointment remains Pending

### Requirement: Customers cancel eligible appointments

The system SHALL allow a Customer to cancel their own appointment while it is Pending or Confirmed and more than 2 hours remain before its start. After that cutoff the request MUST be refused. (Proposed assumption A4.)

#### Scenario: Customer cancels before the cutoff
- **WHEN** a customer cancels their own confirmed appointment more than 2 hours before the start
- **THEN** the appointment becomes Cancelled and its slot is released

#### Scenario: Customer cancels inside the cutoff
- **WHEN** a customer cancels within 2 hours of the start
- **THEN** the request is refused and the appointment is unchanged

#### Scenario: Customer cancels another customer's appointment
- **WHEN** a customer targets an appointment they do not own
- **THEN** the request is rejected as forbidden

### Requirement: Providers cancel their own confirmed appointments before the end

The system SHALL allow the owning provider to cancel a Confirmed appointment while the current time is before its end time. After the end time the only permitted action SHALL be completion. (Proposed rule.)

#### Scenario: Provider cancels in advance
- **WHEN** a provider cancels their own confirmed appointment before it ends
- **THEN** the appointment becomes Cancelled and its slot is released

#### Scenario: Cancellation after the end time is refused
- **WHEN** a provider attempts to cancel a confirmed appointment whose end time has passed
- **THEN** the request is refused

### Requirement: Providers complete confirmed appointments after the end time

The system SHALL allow the owning provider to mark a Confirmed appointment Completed only when the current time is at or after its end time. No other role may complete an appointment, and completion MUST NOT occur automatically.

#### Scenario: Completion after the end time
- **WHEN** a provider marks a confirmed appointment completed after it has ended
- **THEN** the appointment becomes Completed

#### Scenario: Premature completion is refused
- **WHEN** a provider attempts to complete an appointment that has not yet ended
- **THEN** the request is refused

#### Scenario: No automatic completion
- **WHEN** a confirmed appointment's end time passes with no provider action
- **THEN** the appointment remains Confirmed until the provider acts

### Requirement: Cancellation records who cancelled

Every cancellation SHALL record whether it was performed by a customer, a provider or an administrator, identify the acting account, and accept an optional reason. The reason MUST NOT be mandatory. (Proposed assumption A7.)

#### Scenario: Cancellation by each role is attributed
- **WHEN** a customer, provider or administrator cancels an appointment
- **THEN** the recorded actor role matches the role that performed it

#### Scenario: Cancellation without a reason
- **WHEN** a cancellation is submitted with no reason
- **THEN** the cancellation succeeds

### Requirement: Rescheduling creates a linked successor appointment

The system SHALL implement rescheduling by marking the original appointment Rescheduled and creating a new appointment in Pending that references the original. The successor SHALL keep the same customer, provider and service, SHALL change only the time, and SHALL follow the same expiry rules as a new booking. (Proposed assumption A9.)

#### Scenario: Original is preserved
- **WHEN** a customer reschedules an appointment
- **THEN** the original remains retrievable with its original time and the Rescheduled status

#### Scenario: Successor starts pending
- **WHEN** a reschedule succeeds
- **THEN** the successor is Pending and requires provider confirmation

#### Scenario: Links are visible in both directions
- **WHEN** either the original or the successor is opened
- **THEN** the relationship to the other appointment is available

#### Scenario: Provider and service cannot change
- **WHEN** a reschedule request names a different provider or service
- **THEN** the request is rejected

### Requirement: Rescheduling is atomic

Releasing the original slot and claiming the new slot SHALL succeed or fail together. If the new slot is unavailable or any validation fails, the original appointment MUST remain unchanged.

#### Scenario: New slot is taken
- **WHEN** the requested new slot becomes unavailable before the reschedule completes
- **THEN** the operation fails, the original appointment is unchanged and the customer is told the slot is unavailable

#### Scenario: Invalid new time
- **WHEN** the new time is outside availability, beyond the horizon, inside the notice period or after the cutoff
- **THEN** the operation fails and the original appointment is unchanged

#### Scenario: Duplicate reschedule submission
- **WHEN** the same reschedule is submitted twice
- **THEN** only one successor exists and the second attempt is refused

#### Scenario: Rejection does not restore the original
- **WHEN** a provider rejects a successor appointment
- **THEN** the original remains Rescheduled and the customer has no active appointment

### Requirement: Appointment history records every transition

The system SHALL record an append-only event for every status transition, including the previous status, the new status, the acting account or system, the actor role, an optional reason and a timestamp.

#### Scenario: Transition is recorded
- **WHEN** an appointment changes status
- **THEN** an event capturing the transition and actor is appended

#### Scenario: Reschedule records both sides
- **WHEN** an appointment is rescheduled
- **THEN** the event history shows the original being rescheduled and the successor being created

### Requirement: Customers see their appointments grouped and filterable

The customer dashboard SHALL present upcoming appointments separately from past and cancelled ones, allow filtering by date and status, allow opening an appointment's details, and expose cancel and reschedule only for eligible appointments.

#### Scenario: Upcoming and past are separated
- **WHEN** a customer opens the dashboard
- **THEN** appointments whose end time is in the future are shown as upcoming and earlier ones as past

#### Scenario: Ineligible actions are not offered
- **WHEN** an appointment is inside the cancellation cutoff or is terminal
- **THEN** cancel and reschedule are not offered for it

#### Scenario: Filter by status
- **WHEN** a customer filters by Cancelled
- **THEN** only cancelled appointments are listed

#### Scenario: Empty list
- **WHEN** a customer has no appointments in the selected view
- **THEN** the dashboard reports that there are none

### Requirement: Providers see their working day and pending requests

The provider dashboard SHALL present today's appointments in the provider's local day, upcoming appointments, pending requests requiring action, and a separate group for confirmed appointments whose end time has passed and which await completion.

#### Scenario: Today is computed in the provider timezone
- **WHEN** a provider opens the dashboard
- **THEN** "today" spans local midnight to local midnight in the provider's timezone

#### Scenario: Pending requests are actionable
- **WHEN** pending requests exist
- **THEN** each can be confirmed or rejected from the dashboard

#### Scenario: Awaiting completion is separate
- **WHEN** a confirmed appointment's end time has passed
- **THEN** it appears in the awaiting-completion group and not in the availability-conflict group
