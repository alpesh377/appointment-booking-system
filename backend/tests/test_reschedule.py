from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from tests.conftest import future_slot, login, make_user, post

from app.db import SessionLocal
from app.models import Appointment, AppointmentStatus, Role, User
from app.services.booking import reschedule

UTC = timezone.utc


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


def _availability(client, provider_setup, day):
    return client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
        },
    ).json()["slots"]


def test_reschedule_creates_a_linked_successor(client, db, customer, provider_setup):
    login(client, customer.email)
    original_start = future_slot(days=3, hour=10)
    original = _book(client, provider_setup, original_start)
    new_start = future_slot(days=4, hour=11)

    response = post(
        client, f"/api/appointments/{original['id']}/reschedule", json={"starts_at": new_start.isoformat()}
    )
    assert response.status_code == 200, response.text
    successor = response.json()
    assert successor["status"] == "PENDING"
    assert successor["rescheduled_from_id"] == original["id"]
    assert successor["starts_at"] == new_start.isoformat()
    assert successor["provider"]["id"] == original["provider"]["id"]
    assert successor["service"]["id"] == original["service"]["id"]

    original_detail = client.get(f"/api/appointments/{original['id']}").json()
    assert original_detail["status"] == "RESCHEDULED"
    assert original_detail["rescheduled_to_id"] == successor["id"]
    assert [event["to_status"] for event in original_detail["events"]] == [
        "PENDING",
        "RESCHEDULED",
    ]
    assert [event["to_status"] for event in successor["events"]] == ["PENDING"]


def test_reschedule_frees_the_original_slot_and_claims_the_new_one(client, db, customer, provider_setup):
    login(client, customer.email)
    original_day = (future_slot(days=3, hour=10)).date()
    new_day = (future_slot(days=4, hour=11)).date()
    original = _book(client, provider_setup, future_slot(days=3, hour=10))
    assert future_slot(days=3, hour=10).isoformat() not in _availability(client, provider_setup, original_day)

    post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={"starts_at": future_slot(days=4, hour=11).isoformat()},
    )
    assert future_slot(days=3, hour=10).isoformat() in _availability(client, provider_setup, original_day)
    assert future_slot(days=4, hour=11).isoformat() not in _availability(client, provider_setup, new_day)


def test_reschedule_rejects_a_taken_slot_atomically(client, db, customer, provider_setup):
    other = make_user(db, Role.CUSTOMER.value, "other@example.com")
    login(client, other.email)
    target = future_slot(days=4, hour=11)
    _book(client, provider_setup, target)
    post(client, "/api/auth/logout")

    login(client, customer.email)
    original_start = future_slot(days=3, hour=10)
    original = _book(client, provider_setup, original_start)
    response = post(
        client, f"/api/appointments/{original['id']}/reschedule", json={"starts_at": target.isoformat()}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "SLOT_UNAVAILABLE"

    detail = client.get(f"/api/appointments/{original['id']}").json()
    assert detail["status"] == "PENDING"
    assert detail["rescheduled_to_id"] is None
    with SessionLocal() as session:
        count = session.execute(
            select(func.count()).select_from(Appointment).where(
                Appointment.rescheduled_from_id == original["id"]
            )
        ).scalar_one()
    assert count == 0


def test_reschedule_outside_availability_is_rejected(client, db, customer, provider_setup):
    login(client, customer.email)
    original = _book(client, provider_setup, future_slot(days=3, hour=10))
    response = post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={"starts_at": future_slot(days=4, hour=3).isoformat()},
    )
    assert response.status_code == 409
    assert client.get(f"/api/appointments/{original['id']}").json()["status"] == "PENDING"


def test_reschedule_inside_the_cutoff_is_refused(client, db, customer, provider_setup):
    appointment = Appointment(
        customer_id=customer.id,
        provider_id=provider_setup["profile"].id,
        service_id=provider_setup["service"].id,
        starts_at=datetime.now(UTC) + timedelta(hours=1),
        ends_at=datetime.now(UTC) + timedelta(hours=2),
        duration_minutes=60,
        status=AppointmentStatus.PENDING.value,
    )
    db.add(appointment)
    db.commit()
    login(client, customer.email)
    response = post(
        client,
        f"/api/appointments/{appointment.id}/reschedule",
        json={"starts_at": future_slot(days=4, hour=11).isoformat()},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "CUTOFF_PASSED"


def test_reschedule_cannot_change_provider_or_service(client, db, customer, provider_setup):
    login(client, customer.email)
    original = _book(client, provider_setup, future_slot(days=3, hour=10))
    response = post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={
            "starts_at": future_slot(days=4, hour=11).isoformat(),
            "provider_id": str(provider_setup["profile"].id),
        },
    )
    assert response.status_code == 422


def test_duplicate_reschedule_is_refused(client, db, customer, provider_setup):
    login(client, customer.email)
    original = _book(client, provider_setup, future_slot(days=3, hour=10))
    first = post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={"starts_at": future_slot(days=4, hour=11).isoformat()},
    )
    assert first.status_code == 200
    second = post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={"starts_at": future_slot(days=5, hour=11).isoformat()},
    )
    assert second.status_code == 409


def test_rejected_successor_does_not_restore_the_original(client, db, customer, provider_setup):
    login(client, customer.email)
    original = _book(client, provider_setup, future_slot(days=3, hour=10))
    successor = post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={"starts_at": future_slot(days=4, hour=11).isoformat()},
    ).json()
    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)
    rejected = post(client, f"/api/appointments/{successor['id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"

    assert client.get(f"/api/appointments/{original['id']}").json()["status"] == "RESCHEDULED"
    post(client, "/api/auth/logout")
    login(client, customer.email)
    dashboard = client.get("/api/dashboard/customer").json()
    assert dashboard["upcoming"] == []


def test_reschedule_requires_ownership(client, db, customer, provider_setup):
    login(client, customer.email)
    original = _book(client, provider_setup, future_slot(days=3, hour=10))
    post(client, "/api/auth/logout")
    other = make_user(db, Role.CUSTOMER.value, "other@example.com")
    login(client, other.email)
    response = post(
        client,
        f"/api/appointments/{original['id']}/reschedule",
        json={"starts_at": future_slot(days=4, hour=11).isoformat()},
    )
    assert response.status_code == 403


def test_concurrent_reschedules_produce_one_successor(db, customer, provider_setup):
    from app.core.errors import AppError

    original = Appointment(
        customer_id=customer.id,
        provider_id=provider_setup["profile"].id,
        service_id=provider_setup["service"].id,
        starts_at=future_slot(days=3, hour=10),
        ends_at=future_slot(days=3, hour=11),
        duration_minutes=60,
        status=AppointmentStatus.PENDING.value,
    )
    db.add(original)
    db.commit()

    targets = [future_slot(days=4, hour=11), future_slot(days=5, hour=11)]
    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def worker(target):
        session = SessionLocal()
        try:
            user = session.get(User, customer.id)
            appointment = session.get(Appointment, original.id)
            barrier.wait(timeout=10)
            try:
                reschedule(session, user, appointment, target)
                outcome = "ok"
            except AppError as exc:
                outcome = exc.code
        finally:
            session.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(target,)) for target in targets]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(results) == ["INVALID_TRANSITION", "ok"]
    with SessionLocal() as session:
        count = session.execute(
            select(func.count()).select_from(Appointment).where(
                Appointment.rescheduled_from_id == original.id
            )
        ).scalar_one()
    assert count == 1
