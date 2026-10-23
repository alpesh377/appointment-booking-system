from __future__ import annotations

from tests.conftest import (
    DEFAULT_PASSWORD,
    TEST_ORIGIN,
    csrf_headers,
    login,
    make_user,
    post,
)

from app.models import Role


def test_registration_creates_a_customer_and_signs_in(client):
    response = post(
        client,
        "/api/auth/register",
        json={"email": "new@example.com", "password": DEFAULT_PASSWORD, "full_name": "New Person"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "CUSTOMER"
    assert client.get("/api/auth/me").status_code == 200


def test_registration_ignores_a_requested_role(client):
    response = post(
        client,
        "/api/auth/register",
        json={
            "email": "sneaky@example.com",
            "password": DEFAULT_PASSWORD,
            "role": "PROVIDER",
        },
    )
    assert response.status_code == 200
    assert response.json()["role"] == "CUSTOMER"


def test_duplicate_email_in_another_case_is_rejected(client):
    first = post(
        client,
        "/api/auth/register",
        json={"email": "dupe@example.com", "password": DEFAULT_PASSWORD},
    )
    assert first.status_code == 200
    second = post(
        client,
        "/api/auth/register",
        json={"email": "DUPE@example.com", "password": DEFAULT_PASSWORD},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "EMAIL_TAKEN"


def test_short_password_is_rejected(client):
    response = post(
        client,
        "/api/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_invalid_credentials_use_a_generic_message(client, db):
    make_user(db, Role.CUSTOMER.value, "known@example.com")
    unknown = login(client, "nobody@example.com")
    wrong = login(client, "known@example.com", "wrong-password")
    assert unknown.status_code == 401
    assert wrong.status_code == 401
    assert unknown.json()["message"] == wrong.json()["message"]


def test_logout_invalidates_the_session(client, db):
    make_user(db, Role.CUSTOMER.value, "logout@example.com")
    assert login(client, "logout@example.com").status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert post(client, "/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_deactivated_account_cannot_sign_in(client, db):
    make_user(db, Role.CUSTOMER.value, "inactive@example.com", active=False)
    response = login(client, "inactive@example.com")
    assert response.status_code == 403
    assert response.json()["code"] == "ACCOUNT_INACTIVE"


def test_profile_update_is_limited_to_the_current_account(client, db):
    make_user(db, Role.CUSTOMER.value, "profile@example.com")
    login(client, "profile@example.com")
    response = client.patch(
        "/api/auth/me",
        json={"full_name": "Updated Name"},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


def test_csrf_rejects_missing_or_wrong_origin(client):
    missing = client.post("/api/auth/logout")
    assert missing.status_code == 403
    assert missing.json()["code"] == "CSRF_ORIGIN_MISMATCH"

    wrong = client.post(
        "/api/auth/logout",
        headers={"Origin": "https://evil.example", "X-CSRF-Token": client.cookies.get("csrf_token")},
    )
    assert wrong.status_code == 403
    assert wrong.json()["code"] == "CSRF_ORIGIN_MISMATCH"


def test_csrf_rejects_missing_or_mismatched_token(client):
    missing = client.post("/api/auth/logout", headers={"Origin": TEST_ORIGIN})
    assert missing.status_code == 403
    assert missing.json()["code"] == "CSRF_TOKEN_INVALID"

    mismatched = client.post(
        "/api/auth/logout",
        headers={"Origin": TEST_ORIGIN, "X-CSRF-Token": "not-the-cookie"},
    )
    assert mismatched.status_code == 403
    assert mismatched.json()["code"] == "CSRF_TOKEN_INVALID"


def test_csrf_accepts_a_valid_pair_and_exempts_safe_methods(client):
    assert client.get("/api/health").status_code == 200
    response = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert response.status_code == 200


def test_role_authorization_is_enforced_server_side(client, db):
    make_user(db, Role.CUSTOMER.value, "notadmin@example.com")
    login(client, "notadmin@example.com")
    response = client.get("/api/admin/stats")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_unauthenticated_requests_are_rejected(client):
    response = client.get("/api/appointments")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
