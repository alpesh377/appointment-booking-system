# Spec Delta

## Purpose

Refines how the web surface presents progress, results, operations and motion: live search, skeleton placeholders, toast-based operation feedback with optimistic updates, slot-grouped booking selection, and a motion policy that respects reduced-motion preferences.

## ADDED Requirements

### Requirement: Provider names and categories are searchable while typing

The provider listing SHALL narrow the displayed results while the user types into the search field, without requiring a submit action, and SHALL state the number of matching providers.

#### Scenario: Typing narrows results
- **WHEN** a user types a partial provider name or category
- **THEN** the displayed providers are reduced to the matching subset without pressing a button

#### Scenario: Count is announced
- **WHEN** the result set changes from a search
- **THEN** the number of matching providers is available to assistive technology

#### Scenario: Clearing restores the full list
- **WHEN** the search field is cleared
- **THEN** the full provider list is displayed again

### Requirement: Loading data views show layout placeholders

A data view whose content is loading MAY use layout placeholders (skeletons) matching the shape of the expected content in place of a text prompt; when placeholders are used they MUST occupy the region where content will appear until data or an error replaces it.

#### Scenario: Grid list loading
- **WHEN** a card grid such as the provider listing is loading
- **THEN** placeholder cards are displayed in the positions the results will occupy

#### Scenario: Placeholder is not mistaken for content
- **WHEN** placeholders are shown
- **THEN** they are not announced as content and are replaced once the data arrives

### Requirement: Operations confirm success and report failure as notifications

Every state-changing operation (create, update, delete, confirm, reject, complete, reschedule, cancel) SHALL report its outcome via a transient notification: success acknowledged, failure named. A failure MUST leave the previously displayed data intact or identically restored.

#### Scenario: Successful save is acknowledged
- **WHEN** a mutation completes successfully
- **THEN** a transient confirmation appears naming what succeeded and the interface reflects the new state

#### Scenario: Failed save is reported and rolled back
- **WHEN** a mutation fails
- **THEN** a transient error names the failure and the list or record displays its prior state again

#### Scenario: Notifications are dismissible
- **WHEN** a transient notification is displayed
- **THEN** it can be dismissed by the user and disappears on its own after a reasonable time

### Requirement: Booking slot selection is grouped and summarised

The booking interface SHALL present the optional starting times grouped by part of the day, SHALL keep the currently selected slot visibly marked, and SHALL show a summary of the pending choice (provider, service, duration, date and time) alongside the submit action until submission. Changing the service or date clears the stale selection rather than submitting it.

#### Scenario: Slots are grouped by time of day
- **WHEN** a date with available times is open
- **THEN** the times are grouped by part of the day so related times sit together

#### Scenario: Selection stays visible
- **WHEN** a slot is chosen
- **THEN** it remains visually marked and the summary shows the full pending choice

#### Scenario: Stale selection is dropped
- **WHEN** the service or date changes after a slot was selected
- **THEN** the old selection is cleared and submission is not possible until a new slot is chosen

### Requirement: Motion is subtle and honours reduced-motion preference

Entrance, hover, selection and status-change animations SHALL be short and non-blocking. When the operating system requests reduced motion, the interface MUST present the same content and controls without entrance or transition animations.

#### Scenario: Reduced motion is requested
- **WHEN** the OS-level reduced-motion preference is enabled
- **THEN** pages and lists appear without entrance animations and every control remains operable

#### Scenario: Animations do not delay interaction
- **WHEN** a list or section animates into view with the preference not set
- **THEN** its content is operable without waiting for the animation to finish
