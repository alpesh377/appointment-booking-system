from __future__ import annotations

from app.models import Role

from tests.conftest import DEFAULT_PASSWORD, login, make_user, patch, post


def _admin(db):
    return make_user(db, Role.ADMIN.value, "admin@example.com", name="Ada Admin")


def _create_provider(client, email="doc@example.com", category="Dentistry"):
    return post(
        client,
        "/api/providers",
        json={
            "email": email,
            "password": DEFAULT_PASSWORD,
            "full_name": "Doc Tor",
            "display_name": "Dr Doc",
            "category": category,
            "timezone": "UTC",
        },
    )


def test_admin_creates_a_provider_who_can_sign_in(client, db):
    _admin(db)
    login(client, "admin@example.com")
    response = _create_provider(client)
    assert response.status_code == 201
    assert response.json()["display_name"] == "Dr Doc"

    post(client, "/api/auth/logout")
    assert login(client, "doc@example.com").status_code == 200
    assert client.get("/api/auth/me").json()["role"] == "PROVIDER"


def test_customer_cannot_create_a_provider(client, db):
    make_user(db, Role.CUSTOMER.value, "c@example.com")
    login(client, "c@example.com")
    assert _create_provider(client).status_code == 403


def test_listing_shows_active_providers_only(client, db):
    _admin(db)
    login(client, "admin@example.com")
    created = _create_provider(client).json()
    assert len(client.get("/api/providers").json()) == 1

    post(client, f"/api/providers/{created['id']}/deactivate")
    assert client.get("/api/providers").json() == []
    assert client.get(f"/api/providers/{created['id']}").status_code == 404


def test_search_matches_name_and_service_category(client, db, provider_setup):
    assert len(client.get("/api/providers", params={"q": "provider"}).json()) == 1
    assert len(client.get("/api/providers", params={"q": "general"}).json()) == 1
    assert client.get("/api/providers", params={"q": "zzz"}).json() == []


def test_service_duration_must_be_a_multiple_of_five_within_bounds(client, db, provider_setup):
    login(client, provider_setup["user"].email)
    provider_id = str(provider_setup["profile"].id)
    for duration in (14, 485, 17):
        response = post(
            client,
            f"/api/providers/{provider_id}/services",
            json={"name": "X", "category": "Y", "duration_minutes": duration},
        )
        assert response.status_code == 422, duration
    ok = post(
        client,
        f"/api/providers/{provider_id}/services",
        json={"name": "X", "category": "Y", "duration_minutes": 15},
    )
    assert ok.status_code == 201


def test_admin_cannot_manage_operational_services(client, db, provider_setup):
    _admin(db)
    login(client, "admin@example.com")
    response = post(
        client,
        f"/api/providers/{provider_setup['profile'].id}/services",
        json={"name": "X", "category": "Y", "duration_minutes": 30},
    )
    assert response.status_code == 403


def test_provider_cannot_edit_another_provider(client, db, provider_setup):
    other = make_user(db, Role.PROVIDER.value, "other@example.com", name="Other")
    login(client, provider_setup["user"].email)
    response = patch(
        client,
        f"/api/providers/{other.provider_profile.id}",
        json={"display_name": "Hijacked"},
    )
    assert response.status_code == 403


def test_provider_updates_own_profile(client, db, provider_setup):
    login(client, provider_setup["user"].email)
    response = patch(
        client,
        f"/api/providers/{provider_setup['profile'].id}",
        json={"display_name": "Renamed", "timezone": "Europe/Berlin"},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Renamed"
    assert response.json()["timezone"] == "Europe/Berlin"


def test_admin_updates_a_provider_profile(client, db, provider_setup):
    _admin(db)
    login(client, "admin@example.com")
    response = patch(
        client,
        f"/api/providers/{provider_setup['profile'].id}",
        json={"display_name": "Admin Renamed", "category": "Updated"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Admin Renamed"
    assert response.json()["category"] == "Updated"
    assert (
        client.get(f"/api/providers/{provider_setup['profile'].id}").json()["display_name"] == "Admin Renamed"
    )


def test_invalid_timezone_is_rejected(client, db, provider_setup):
    login(client, provider_setup["user"].email)
    response = patch(
        client,
        f"/api/providers/{provider_setup['profile'].id}",
        json={"timezone": "Mars/Olympus"},
    )
    assert response.status_code == 422


def test_deactivating_a_provider_preserves_services(client, db, provider_setup):
    _admin(db)
    login(client, "admin@example.com")
    provider_id = str(provider_setup["profile"].id)
    assert post(client, f"/api/providers/{provider_id}/deactivate").status_code == 200
    assert client.get("/api/providers").json() == []
    # The service row still exists; the provider can be reactivated.
    assert post(client, f"/api/providers/{provider_id}/reactivate").status_code == 200
    assert len(client.get("/api/providers").json()) == 1
