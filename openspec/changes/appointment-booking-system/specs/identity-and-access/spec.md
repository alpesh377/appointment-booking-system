# Spec Delta

## Purpose

Governs who may use the system: how accounts are created, how a session begins and ends, which single role an account holds, and how the server decides whether an operation is permitted.

## ADDED Requirements

### Requirement: Public registration creates customer accounts only

The system SHALL create a Customer account for every successful public registration. Registration MUST NOT accept a role from the client, and MUST NOT allow a visitor to obtain an Admin or Service Provider account.

#### Scenario: Visitor registers successfully
- **WHEN** a visitor submits a valid email and password to the registration endpoint
- **THEN** a Customer account is created and the visitor becomes authenticated

#### Scenario: Registration attempts to request a provider role
- **WHEN** a registration request includes a provider or admin role
- **THEN** the resulting account holds the Customer role regardless of the submitted value

#### Scenario: Duplicate email is rejected
- **WHEN** a visitor registers with an email that already exists in any letter case
- **THEN** the request is rejected with a conflict error and no second account is created

### Requirement: Sign-in establishes an authenticated session

The system SHALL authenticate an account by email and password and, on success, establish a session that authorizes subsequent requests. Invalid credentials MUST be rejected without revealing whether the email exists.

#### Scenario: Valid credentials
- **WHEN** an active account submits its correct email and password
- **THEN** a session is established and authenticated requests succeed

#### Scenario: Invalid credentials
- **WHEN** a request supplies an unknown email or a wrong password
- **THEN** authentication fails with one generic message that does not distinguish the two cases

### Requirement: Sign-out ends the session

The system SHALL end the authenticated session when the user signs out, and subsequent protected requests MUST be rejected.

#### Scenario: Sign-out invalidates access
- **WHEN** an authenticated user signs out and then requests a protected resource
- **THEN** the request is rejected as unauthenticated

### Requirement: Each account holds exactly one role

The system SHALL assign exactly one of Admin, Service Provider or Customer to every account. An account MUST NOT hold multiple roles, and role MUST NOT be changeable through any application interface.

#### Scenario: Role determines accessible areas
- **WHEN** an authenticated account requests an area belonging to a different role
- **THEN** the request is rejected as forbidden

#### Scenario: No role-change operation exists
- **WHEN** any client attempts to alter the role of an existing account
- **THEN** the role remains unchanged

### Requirement: Administrators create provider accounts

The system SHALL allow an Administrator to create a Service Provider account together with its provider profile, supplying an initial password. Provider accounts MUST NOT be creatable through public registration.

#### Scenario: Administrator creates a provider
- **WHEN** an Administrator submits a new provider's identity and profile data
- **THEN** a provider account and its profile are created and the provider can sign in

#### Scenario: A customer cannot create a provider
- **WHEN** a Customer account attempts to create a provider account
- **THEN** the request is rejected as forbidden

### Requirement: Users manage their own profile

The system SHALL allow an authenticated user to view and update their own profile. A user MUST NOT view or update another user's profile.

#### Scenario: User updates own profile
- **WHEN** an authenticated user submits valid changes to their own profile
- **THEN** the changes are persisted and returned

#### Scenario: User targets another profile
- **WHEN** an authenticated user requests or modifies another account's profile
- **THEN** the request is rejected as forbidden

### Requirement: Authorization is enforced by the server

The system SHALL verify authentication, role and resource ownership on the server for every protected page and API operation, and MUST reject unauthorized access even when the client does not expose the corresponding control.

#### Scenario: Cross-customer access is denied
- **WHEN** a Customer requests an appointment belonging to another customer
- **THEN** the request is rejected and no appointment data is returned

#### Scenario: Unauthenticated API access is denied
- **WHEN** an unauthenticated request targets a protected API operation
- **THEN** the request is rejected as unauthenticated

### Requirement: Deactivated accounts cannot act

A deactivated account MUST be refused authentication and MUST NOT perform authenticated operations. Its appointment records and history SHALL remain intact and visible to authorized roles.

#### Scenario: Deactivated account signs in
- **WHEN** a deactivated account submits valid credentials
- **THEN** authentication is refused

#### Scenario: History survives deactivation
- **WHEN** an Administrator views appointments belonging to a deactivated customer or provider
- **THEN** those appointments and their history are still available

### Requirement: The first administrator is provisioned without default credentials

The system SHALL provision the initial Administrator through a documented setup command using operator-supplied credentials. No default administrator password SHALL exist in the repository or in a database migration.

#### Scenario: Setup command creates the first administrator
- **WHEN** an operator runs the documented setup command with credentials supplied through configuration
- **THEN** a single active Administrator account exists and can sign in

#### Scenario: Setup without credentials fails safely
- **WHEN** the setup command runs without the required credential configuration
- **THEN** it exits with a clear error and creates no account

### Requirement: Sessions are protected against script access and cross-site request forgery

The system SHALL transmit the session credential in a cookie that client-side scripts cannot read, and SHALL verify every state-changing request with both a same-origin check and a CSRF token. SameSite behaviour alone MUST NOT be treated as sufficient protection.

#### Scenario: Cross-origin state change is rejected
- **WHEN** a state-changing request arrives with an Origin that does not match the application origin
- **THEN** the request is rejected as forbidden and no state changes

#### Scenario: Missing or mismatched CSRF token is rejected
- **WHEN** a state-changing request omits the CSRF token or presents one that does not match the issued token
- **THEN** the request is rejected as forbidden

#### Scenario: Valid same-origin request succeeds
- **WHEN** a state-changing request presents the matching Origin and CSRF token
- **THEN** the request proceeds subject to authentication and authorization

#### Scenario: Safe methods are exempt
- **WHEN** a read-only request is issued without a CSRF token
- **THEN** it is processed normally

### Requirement: Passwords are stored irreversibly

The system SHALL store passwords only as salted, memory-hard hashes and MUST reject passwords shorter than eight characters at registration and at password change. (Proposed default U6.)

#### Scenario: Password is never stored or returned in plaintext
- **WHEN** an account is created or its password changed
- **THEN** the stored value is a one-way hash and no API response contains the password

#### Scenario: Short password is rejected
- **WHEN** registration or a password change submits fewer than eight characters
- **THEN** the request is rejected with a validation error
