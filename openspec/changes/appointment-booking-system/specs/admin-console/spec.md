# Spec Delta

## Purpose

Defines the administrator's view of the platform: aggregate totals and statistics, whole-platform appointment visibility, customer account administration, and the single supervisory action an administrator may take on an appointment.

## ADDED Requirements

### Requirement: Administrators see platform totals

The admin dashboard SHALL display the total number of customers, service providers and appointments.

#### Scenario: Totals are displayed
- **WHEN** an Administrator opens the dashboard
- **THEN** customer, provider and appointment counts are shown

#### Scenario: Totals reflect deactivated accounts
- **WHEN** an account is deactivated
- **THEN** it remains counted as an existing record

### Requirement: Administrators see aggregate appointment statistics

The admin dashboard SHALL present appointment statistics covering at least the distribution of appointments by status.

#### Scenario: Status distribution is shown
- **WHEN** an Administrator opens the statistics section
- **THEN** counts per appointment status are displayed

### Requirement: Administrators view and filter all appointments

The system SHALL allow an Administrator to view every appointment, including those belonging to deactivated accounts, and filter them by provider, customer, date and status.

#### Scenario: Filters combine
- **WHEN** an Administrator filters by provider, date range and status together
- **THEN** only appointments satisfying every filter are listed

#### Scenario: Appointment details are available
- **WHEN** an Administrator opens an appointment
- **THEN** its provider, customer, service, times and status are shown

#### Scenario: Large results are paginated
- **WHEN** more appointments match than fit on one page
- **THEN** results are paginated and the total count is available

### Requirement: Administrators list and deactivate customer accounts

The system SHALL allow an Administrator to list customer accounts and deactivate them. Deactivation MUST NOT delete the account or its appointment history.

#### Scenario: Customer is deactivated
- **WHEN** an Administrator deactivates a customer
- **THEN** the customer can no longer sign in and their appointments remain intact

#### Scenario: Reactivation restores access
- **WHEN** an Administrator reactivates a customer
- **THEN** the customer can sign in again

### Requirement: Administrators cancel appointments as a supervisory action

The system SHALL allow an Administrator to cancel any Pending or Confirmed appointment at any time. The cancellation SHALL record the administrator as the actor and MUST NOT be recorded as a provider rejection.

#### Scenario: Administrator cancels a confirmed appointment
- **WHEN** an Administrator cancels a confirmed appointment
- **THEN** it becomes Cancelled and the actor is recorded as an administrator

#### Scenario: Cancelling a pending request
- **WHEN** an Administrator cancels a pending request
- **THEN** it becomes Cancelled and not Rejected

#### Scenario: Terminal appointments cannot be cancelled
- **WHEN** an Administrator attempts to cancel an appointment in a terminal status
- **THEN** the request is refused

### Requirement: Administrators cannot act on behalf of customers or providers

An Administrator MUST NOT confirm, reject, complete or reschedule an appointment, and MUST NOT change a provider's services or availability.

#### Scenario: Administrative confirmation is refused
- **WHEN** an Administrator attempts to confirm a pending request
- **THEN** the request is rejected as forbidden

#### Scenario: Administrative completion is refused
- **WHEN** an Administrator attempts to mark an appointment completed
- **THEN** the request is rejected as forbidden

#### Scenario: Administrative reschedule is refused
- **WHEN** an Administrator attempts to reschedule an appointment
- **THEN** the request is rejected as forbidden

### Requirement: Roles cannot be changed and records cannot be hard-deleted

The system MUST NOT provide any operation that changes an account's role or permanently deletes a user, provider or service that has history.

#### Scenario: Role change is refused
- **WHEN** any client attempts to change an account's role
- **THEN** the request is rejected and the role is unchanged

#### Scenario: Hard delete is refused
- **WHEN** an Administrator attempts to permanently delete an account or service
- **THEN** the operation is refused or performed as deactivation

### Requirement: Deactivation with future appointments requires follow-up

Deactivating a customer or provider who has future active appointments SHALL be permitted. The affected appointments MUST NOT be cancelled automatically and SHALL be surfaced to the Administrator for manual resolution.

#### Scenario: Provider deactivation surfaces appointments
- **WHEN** an Administrator deactivates a provider who has future confirmed appointments
- **THEN** those appointments remain confirmed and are listed for manual action

#### Scenario: Customer deactivation surfaces appointments
- **WHEN** an Administrator deactivates a customer who has future appointments
- **THEN** those appointments remain unchanged and are listed for manual action

### Requirement: The last active administrator cannot be removed

The system MUST prevent an Administrator from deactivating their own account and MUST prevent deactivation of the final active Administrator.

#### Scenario: Self-deactivation is refused
- **WHEN** an Administrator attempts to deactivate their own account
- **THEN** the request is refused

#### Scenario: Last administrator is protected
- **WHEN** deactivating an account would leave no active Administrator
- **THEN** the request is refused

### Requirement: Administrative reasons are prompted but optional

Administrative actions that accept a reason SHALL proceed when no reason is supplied. (Proposed assumption A7.)

#### Scenario: Action without a reason succeeds
- **WHEN** an Administrator cancels an appointment and leaves the reason empty
- **THEN** the cancellation succeeds
