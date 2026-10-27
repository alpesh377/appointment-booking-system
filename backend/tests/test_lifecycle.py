from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest
from app.models import Appointment, Role

from tests.conftest import future_slot, login, make_user, post


def _book(client, provider_setup, start):
    response = post(
        client,
        "/api/appointments",
        json={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "starts_at": start.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


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


STATUSES = [
    "PENDING",
    "CONFIRMED",
    "REJECTED",
    "CANCELLED",
    "COMPLETED",
    "EXPIRED",
    "RESCHEDULED",
]


@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("action", ["confirm", "reject", "cancel", "complete"])
def test_provider_transition_matrix(client, db, customer, provider_setup, status, action):
    appointment = _insert(db, customer, provider_setup, future_slot(days=3, hour=10), status)
    login(client, provider_setup["user"].email)
    response = post(client, f"/api/appointments/{appointment.id}/{action}")
    legal = (action in {"confirm", "reject"} and status == "PENDING") or (
        action == "cancel" and status == "CONFIRMED"
    )
    # Completion is never legal before the end time, whatever the status.
    if legal:
        assert response.status_code == 200, (status, action, response.text)
    else:
        assert response.status_code == 409, (status, action, response.text)
        assert response.json()["code"] in {"INVALID_TRANSITION", "USE_REJECT"}


@pytest.mark.parametrize("status", STATUSES)
def test_customer_cancel_matrix(client, db, customer, provider_setup, status):
    appointment = _insert(db, customer, provider_setup, future_slot(days=3, hour=10), status)
    login(client, customer.email)
    response = post(client, f"/api/appointments/{appointment.id}/cancel")
    if status in {"PENDING", "CONFIRMED"}:
        assert response.status_code == 200, (status, response.text)
    else:
        assert response.status_code == 409, (status, response.text)


def test_provider_confirms_a_pending_request(client, db, customer, provider_setup):
    login(client, customer.email)
    created = _book(client, provider_setup, future_slot(days=3, hour=10))
    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)

    response = post(client, f"/api/appointments/{created['id']}/confirm")
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    assert [event["to_status"] for event in response.json()["events"]] == [
        "PENDING",
        "CONFIRMED",
    ]


def test_provider_rejects_a_pending_request_and_frees_the_slot(client, db, customer, provider_setup):
    login(client, customer.email)
    start = future_slot(days=3, hour=10)
    created = _book(client, provider_setup, start)
    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)

    response = post(client, f"/api/appointments/{created['id']}/reject", json={"reason": "Busy"})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"

    post(client, "/api/auth/logout")
    login(client, customer.email)
    availability = client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "date_from": start.date().isoformat(),
            "date_to": start.date().isoformat(),
        },
    )
    assert start.isoformat() in availability.json()["slots"]


def test_provider_must_reject_not_cancel_a_pending_request(client, db, customer, provider_setup):
    login(client, customer.email)
    created = _book(client, provider_setup, future_slot(days=3, hour=10))
    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)

    response = post(client, f"/api/appointments/{created['id']}/cancel")
    assert response.status_code == 409
    assert response.json()["code"] == "USE_REJECT"
    assert client.get(f"/api/appointments/{created['id']}").json()["status"] == "PENDING"


def test_customer_cancels_before_the_cutoff(client, db, customer, provider_setup):
    login(client, customer.email)
    created = _book(client, provider_setup, future_slot(days=3, hour=10))
    response = post(client, f"/api/appointments/{created['id']}/cancel", json={"reason": "Plans"})
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancelled_by_role"] == "customer"


def test_customer_cannot_cancel_inside_the_cutoff(client, db, customer, provider_setup):
    appointment = _insert(db, customer, provider_setup, datetime.now(UTC) + timedelta(hours=1), "CONFIRMED")
    login(client, customer.email)
    response = post(client, f"/api/appointments/{appointment.id}/cancel")
    assert response.status_code == 403
    assert response.json()["code"] == "CUTOFF_PASSED"


def test_provider_cancels_a_confirmed_appointment_before_it_ends(client, db, customer, provider_setup):
    login(client, customer.email)
    created = _book(client, provider_setup, future_slot(days=3, hour=10))
    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)
    post(client, f"/api/appointments/{created['id']}/confirm")

    response = post(client, f"/api/appointments/{created['id']}/cancel", json={"reason": "Sick"})
    assert response.status_code == 200
    assert response.json()["cancelled_by_role"] == "provider"


def test_provider_cannot_cancel_after_the_end_time(client, db, customer, provider_setup):
    appointment = _insert(
        db,
        customer,
        provider_setup,
        datetime.now(UTC) - timedelta(hours=2),
        "CONFIRMED",
    )
    login(client, provider_setup["user"].email)
    response = post(client, f"/api/appointments/{appointment.id}/cancel")
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_TRANSITION"


def test_completion_requires_the_end_time_to_have_passed(client, db, customer, provider_setup):
    login(client, customer.email)
    created = _book(client, provider_setup, future_slot(days=3, hour=10))
    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)
    post(client, f"/api/appointments/{created['id']}/confirm")

    early = post(client, f"/api/appointments/{created['id']}/complete")
    assert early.status_code == 409

    past = _insert(db, customer, provider_setup, datetime.now(UTC) - timedelta(hours=2), "CONFIRMED")
    done = post(client, f"/api/appointments/{past.id}/complete")
    assert done.status_code == 200
    assert done.json()["status"] == "COMPLETED"


def test_a_past_confirmed_appointment_is_not_completed_automatically(client, db, customer, provider_setup):
    appointment = _insert(db, customer, provider_setup, datetime.now(UTC) - timedelta(hours=2), "CONFIRMED")
    login(client, provider_setup["user"].email)
    response = client.get(f"/api/appointments/{appointment.id}")
    assert response.json()["status"] == "CONFIRMED"


def test_terminal_states_reject_further_transitions(client, db, customer, provider_setup):
    appointment = _insert(db, customer, provider_setup, future_slot(days=3, hour=10), "CANCELLED")
    login(client, provider_setup["user"].email)
    assert post(client, f"/api/appointments/{appointment.id}/confirm").status_code == 409
    assert post(client, f"/api/appointments/{appointment.id}/reject").status_code == 409
    assert post(client, f"/api/appointments/{appointment.id}/complete").status_code == 409


def test_another_customer_cannot_see_or_cancel(client, db, customer, provider_setup):
    appointment = _insert(db, customer, provider_setup, future_slot(days=3, hour=10), "PENDING")
    other = make_user(db, Role.CUSTOMER.value, "other@example.com")
    login(client, other.email)
    assert client.get(f"/api/appointments/{appointment.id}").status_code == 403
    assert post(client, f"/api/appointments/{appointment.id}/cancel").status_code == 403


def test_another_provider_cannot_act(client, db, customer, provider_setup):
    login(client, customer.email)
    created = _book(client, provider_setup, future_slot(days=3, hour=10))
    post(client, "/api/auth/logout")
    other = make_user(db, Role.PROVIDER.value, "other@example.com", name="Other")
    login(client, other.email)
    response = post(client, f"/api/appointments/{created['id']}/confirm")
    assert response.status_code == 403


def test_customer_dashboard_groups_upcoming_past_and_cancelled(client, db, customer, provider_setup):
    upcoming = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "CONFIRMED")
    past = _insert(db, customer, provider_setup, datetime.now(UTC) - timedelta(days=2), "COMPLETED")
    cancelled = _insert(db, customer, provider_setup, future_slot(days=3, hour=11), "CANCELLED")
    login(client, customer.email)
    body = client.get("/api/dashboard/customer").json()
    assert [a["id"] for a in body["upcoming"]] == [str(upcoming.id)]
    assert [a["id"] for a in body["past"]] == [str(past.id)]
    assert [a["id"] for a in body["cancelled"]] == [str(cancelled.id)]


def test_customer_appointment_filters(client, db, customer, provider_setup):
    pending = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "PENDING")
    _insert(db, customer, provider_setup, future_slot(days=3, hour=10), "CONFIRMED")
    login(client, customer.email)
    body = client.get("/api/appointments", params={"status": "PENDING"}).json()
    assert [a["id"] for a in body] == [str(pending.id)]
    upcoming = client.get("/api/appointments", params={"view": "upcoming"}).json()
    assert len(upcoming) == 2


def test_provider_dashboard_groups(client, db, customer, provider_setup):
    now = datetime.now(UTC)
    today_start = datetime.combine(now.date(), time(9), tzinfo=UTC)
    today = _insert(db, customer, provider_setup, today_start, "CONFIRMED")
    pending = _insert(db, customer, provider_setup, future_slot(days=2, hour=10), "PENDING")
    awaiting = _insert(db, customer, provider_setup, now - timedelta(hours=3), "CONFIRMED")
    login(client, provider_setup["user"].email)
    body = client.get("/api/dashboard/provider").json()
    today_ids = [a["id"] for a in body["today"]]
    assert str(today.id) in today_ids
    assert [a["id"] for a in body["pending"]] == [str(pending.id)]
    assert [a["id"] for a in body["awaiting_completion"]] == [str(awaiting.id)]
    assert "conflicts" in body
