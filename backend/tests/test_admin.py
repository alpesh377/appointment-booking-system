from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import future_slot, login, make_user, patch, post, put

from app.models import Appointment, Role

UTC = timezone.utc


def _admin(db, email="admin@example.com"):
    return make_user(db, Role.ADMIN.value, email, name="Ada Admin")


def _insert(db, customer, provider_setup, starts_at, status, duration=60):
    appointment = Appointment(
        customer_id=customer.id,
        provider_id=provider_setup["profile"].id,
        service_id=provider_setup["service"].id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=duration),
        duration_minutes=duration,
        status=status,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def test_stats_report_totals_and_status_distribution(client, db, customer, provider_setup):
    _admin(db)
    _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "PENDING")
    _insert(db, customer, provider_setup, future_slot(days=3, hour=10), "CONFIRMED")
    login(client, "admin@example.com")
    body = client.get("/api/admin/stats").json()
    assert body["customers"] == 1
    assert body["providers"] == 1
    assert body["appointments"] == 2
    assert body["by_status"]["PENDING"] == 1
    assert body["by_status"]["CONFIRMED"] == 1


def test_deactivating_a_customer_blocks_sign_in_and_preserves_history(client, db, customer, provider_setup):
    _admin(db)
    appointment = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "CONFIRMED")
    login(client, "admin@example.com")
    assert post(client, f"/api/admin/users/{customer.id}/deactivate").status_code == 200
    assert len(client.get("/api/admin/appointments").json()["items"]) == 1

    post(client, "/api/auth/logout")
    assert login(client, customer.email).status_code == 403

    login(client, "admin@example.com")
    assert post(client, f"/api/admin/users/{customer.id}/reactivate").status_code == 200
    post(client, "/api/auth/logout")
    assert login(client, customer.email).status_code == 200


def test_admin_supervisory_cancellation_is_recorded_as_admin(client, db, customer, provider_setup):
    _admin(db)
    appointment = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "PENDING")
    login(client, "admin@example.com")
    response = post(client, f"/api/admin/appointments/{appointment.id}/cancel", json={"reason": "Policy"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CANCELLED"
    assert body["cancelled_by_role"] == "admin"
    assert body["cancellation_reason"] == "Policy"


def test_admin_cannot_act_as_customer_or_provider(client, db, customer, provider_setup):
    _admin(db)
    appointment = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "PENDING")
    login(client, "admin@example.com")
    assert post(client, f"/api/appointments/{appointment.id}/confirm").status_code == 403
    assert post(client, f"/api/appointments/{appointment.id}/reject").status_code == 403
    assert post(client, f"/api/appointments/{appointment.id}/complete").status_code == 403
    assert post(
        client,
        f"/api/appointments/{appointment.id}/reschedule",
        json={"starts_at": future_slot(days=3, hour=10).isoformat()},
    ).status_code == 403


def test_admin_cannot_edit_services_or_availability(client, db, provider_setup):
    _admin(db)
    login(client, "admin@example.com")
    assert post(
        client,
        f"/api/providers/{provider_setup['profile'].id}/services",
        json={"name": "X", "category": "Y", "duration_minutes": 30},
    ).status_code == 403
    assert put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/windows",
        json={"windows": []},
    ).status_code == 403


def test_terminal_appointments_cannot_be_cancelled_by_admin(client, db, customer, provider_setup):
    _admin(db)
    appointment = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "COMPLETED")
    login(client, "admin@example.com")
    response = post(client, f"/api/admin/appointments/{appointment.id}/cancel")
    assert response.status_code == 409


def test_admin_cannot_deactivate_their_own_account(client, db):
    admin = _admin(db)
    login(client, "admin@example.com")
    response = post(client, f"/api/admin/users/{admin.id}/deactivate")
    assert response.status_code == 403
    assert response.json()["code"] == "SELF_DEACTIVATION"


def test_roles_cannot_be_changed(client, db, customer):
    _admin(db)
    login(client, "admin@example.com")
    response = patch(client, f"/api/admin/users/{customer.id}/role", json={"role": "ADMIN"})
    assert response.status_code in {404, 405}


def test_deactivating_a_provider_surfaces_future_appointments(client, db, customer, provider_setup):
    _admin(db)
    appointment = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "CONFIRMED")
    login(client, "admin@example.com")
    assert post(client, f"/api/providers/{provider_setup['profile'].id}/deactivate").status_code == 200
    items = client.get("/api/admin/appointments").json()["items"]
    assert [item["id"] for item in items] == [str(appointment.id)]
    assert items[0]["status"] == "CONFIRMED"


def test_admin_appointment_filters_and_pagination(client, db, customer, provider_setup):
    _admin(db)
    _insert(db, customer, provider_setup, future_slot(days=2, hour=9), "PENDING")
    _insert(db, customer, provider_setup, future_slot(days=3, hour=9), "PENDING")
    _insert(db, customer, provider_setup, future_slot(days=4, hour=9), "CONFIRMED")
    login(client, "admin@example.com")

    filtered = client.get("/api/admin/appointments", params={"status": "PENDING"}).json()
    assert filtered["total"] == 2

    by_provider = client.get(
        "/api/admin/appointments", params={"provider_id": str(provider_setup["profile"].id)}
    ).json()
    assert by_provider["total"] == 3

    paged = client.get(
        "/api/admin/appointments",
        params={"status": "PENDING", "page": 1, "page_size": 1},
    ).json()
    assert len(paged["items"]) == 1
    assert paged["total"] == 2
