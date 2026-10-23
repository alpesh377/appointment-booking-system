# Spec Delta

## Purpose

Describes what customers can discover about service providers and how providers and administrators maintain that information, including the services a provider offers and their durations.

## ADDED Requirements

### Requirement: Customers browse active providers

The system SHALL present a list of active service providers to any visitor. Deactivated providers MUST NOT appear in the list.

#### Scenario: Active providers are listed
- **WHEN** a visitor opens the provider listing
- **THEN** every active provider is shown with a summary that identifies them and the durations they offer

#### Scenario: Deactivated providers are hidden
- **WHEN** a provider has been deactivated
- **THEN** that provider does not appear in the listing or in search results

### Requirement: Provider detail shows profile and services

The system SHALL present a provider's profile together with the services they currently offer. Each service SHALL display its name, category and duration.

#### Scenario: Visitor opens a provider profile
- **WHEN** a visitor opens the detail page of an active provider
- **THEN** the profile and the provider's active services, with their durations, are displayed

#### Scenario: Provider is unavailable
- **WHEN** a visitor requests a deactivated or unknown provider
- **THEN** the system reports that the provider is not available

### Requirement: Providers are searchable by name or service category

The system SHALL match provider search terms against the provider's display name and against the category of their active services, ignoring letter case.

#### Scenario: Search matches a provider name
- **WHEN** a visitor searches using part of an active provider's name
- **THEN** that provider appears in the results

#### Scenario: Search matches a service category
- **WHEN** a visitor searches using a service category offered by a provider
- **THEN** that provider appears in the results

#### Scenario: Search matches nothing
- **WHEN** no active provider matches the search term
- **THEN** the results are empty and the interface reports that no providers were found

### Requirement: Services carry their own duration and category

Every service SHALL have a name, a category and a duration in minutes. The duration SHALL be between 15 and 480 minutes inclusive and a multiple of 5. A provider SHALL NOT have a separate provider-level duration.

#### Scenario: Service is created with a valid duration
- **WHEN** a provider adds a service with a name, category and a duration of 45 minutes
- **THEN** the service is stored and appears in the provider's service list

#### Scenario: Invalid duration is rejected
- **WHEN** a service is submitted with a duration below 15, above 480, or not a multiple of 5
- **THEN** the request is rejected with a validation error

#### Scenario: Provider listing summarises durations
- **WHEN** a provider offers services of 30 and 90 minutes
- **THEN** the provider listing presents a duration summary covering those services

### Requirement: Administrators create provider accounts with a profile

The system SHALL allow an Administrator to create a provider account and its profile in one operation, including a display name and a category.

#### Scenario: Provider is created
- **WHEN** an Administrator submits a new provider's identity, display name and category
- **THEN** the provider account and profile are created and the provider appears in the listing once active

### Requirement: Authorized users update provider profile data

The system SHALL allow an Administrator to update any provider's profile fields, and SHALL allow a Service Provider to update their own profile fields. A Service Provider MUST NOT update another provider's profile.

#### Scenario: Provider updates own profile
- **WHEN** a provider submits valid changes to their own display name, category, contact details or biography
- **THEN** the changes are persisted

#### Scenario: Provider targets another profile
- **WHEN** a provider attempts to change another provider's profile
- **THEN** the request is rejected as forbidden

#### Scenario: Administrator updates a provider profile
- **WHEN** an Administrator submits valid changes to a provider's profile fields
- **THEN** the changes are persisted

### Requirement: Administrators deactivate providers without destroying history

The system SHALL allow an Administrator to deactivate a provider. Deactivation MUST NOT delete the provider, its services, its availability or its appointments, and MUST NOT cancel any appointment automatically.

#### Scenario: Deactivated provider is removed from discovery
- **WHEN** an Administrator deactivates a provider
- **THEN** the provider no longer appears in listings or search and cannot receive new bookings

#### Scenario: Existing appointments survive deactivation
- **WHEN** a provider with future appointments is deactivated
- **THEN** those appointments remain unchanged and are surfaced to the Administrator for manual resolution

### Requirement: Providers maintain their own services

The system SHALL allow a Service Provider to create, update and deactivate their own services. A service referenced by any appointment MUST NOT be hard-deleted.

#### Scenario: Provider deactivates a service
- **WHEN** a provider deactivates a service
- **THEN** the service is no longer offered for new bookings while existing appointments that used it remain intact

#### Scenario: Deleted service would break history
- **WHEN** a request attempts to permanently delete a service referenced by an appointment
- **THEN** the operation is refused or performed as a deactivation

#### Scenario: Administrator cannot manage operational services
- **WHEN** an Administrator attempts to create or change a provider's service or availability
- **THEN** the request is rejected as forbidden
