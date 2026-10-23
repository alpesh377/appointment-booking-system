from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import future_slot, login, make_user, post, utc_today

from app.db import SessionLocal
from app.models import Role, User
from app.services.booking import create_booking

UTC = timezone.utc


def _book(client, provider_setup, starts_at, **extra):
    payload = {
        "provider_id": str(provider_setup["profile"].id),
        "service_id": str(provider_setup["service"].id),
        "starts_at": starts_at.isoformat(),
        **extra,
    }
    return post(client, "/api/appointments", json=payload)


def test_booking_creates_a_pending_appointment_with_a_hold(client, db, customer, provider_setup):
    login(client, customer.email)
    start = future_slot(days=3, hour=10)
    response = _book(client, provider_setup, start)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["duration_minutes"] == 60
    assert body["ends_at"] == (start + timedelta(minutes=60)).isoformat()
    hold = datetime.fromisoformat(body["hold_expires_at"])
    expected = min(datetime.now(UTC) + timedelta(hours=24), start - timedelta(hours=2))
    assert abs((hold - expected).total_seconds()) < 5


def test_client_supplied_end_time_is_ignored(client, db, customer, provider_setup):
    login(client, customer.email)
    start = future_slot(days=3, hour=11)
    response = _book(client, provider_setup, start, ends_at="2000-01-01T00:00:00Z")
    assert response.status_code == 201
    assert response.json()["ends_at"] == (start + timedelta(minutes=60)).isoformat()


def test_booking_requires_a_customer(client, db, provider_setup):
    login(client, provider_setup["user"].email)
    response = _book(client, provider_setup, future_slot(days=3, hour=10))
    assert response.status_code == 403


def test_service_must_belong_to_the_provider(client, db, customer, provider_setup):
    from app.models import Service

    other = make_user(db, Role.PROVIDER.value, "other@example.com", name="Other")
    service = Service(
        provider_id=other.provider_profile.id,
        name="Other",
        category="Other",
        duration_minutes=30,
    )
    db.add(service)
    db.commit()
    login(client, customer.email)
    response = post(
        client,
        "/api/appointments",
        json={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(service.id),
            "starts_at": future_slot(days=3, hour=10).isoformat(),
        },
    )
    assert response.status_code == 404


def test_slot_off_the_grid_is_rejected(client, db, customer, provider_setup):
    login(client, customer.email)
    start = future_slot(days=3, hour=9, minute=15)
    response = _book(client, provider_setup, start)
    assert response.status_code == 409
    assert response.json()["code"] == "SLOT_UNAVAILABLE"


def test_booking_beyond_the_horizon_is_rejected(client, db, customer, provider_setup):
    login(client, customer.email)
    start = datetime.combine(utc_today() + timedelta(days=40), datetime.min.time(), tzinfo=UTC).replace(hour=10)
    response = _book(client, provider_setup, start)
    assert response.status_code == 409
    assert response.json()["code"] == "SLOT_UNAVAILABLE"


def test_deactivated_provider_cannot_be_booked(client, db, customer, provider_setup):
    provider_setup["profile"].is_active = False
    db.commit()
    login(client, customer.email)
    response = _book(client, provider_setup, future_slot(days=3, hour=10))
    assert response.status_code == 404


def test_deactivated_service_cannot_be_booked(client, db, customer, provider_setup):
    provider_setup["service"].is_active = False
    db.commit()
    login(client, customer.email)
    response = _book(client, provider_setup, future_slot(days=3, hour=10))
    assert response.status_code == 409
    assert response.json()["code"] == "SERVICE_INACTIVE"


def test_expired_pending_releases_its_slot_and_is_recorded(client, db, customer, provider_setup):
    login(client, customer.email)
    start = future_slot(days=3, hour=10)
    created = _book(client, provider_setup, start).json()

    db.execute(
        text("UPDATE appointments SET hold_expires_at = now() - interval '1 minute' WHERE id = :id"),
        {"id": created["id"]},
    )
    db.commit()

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

    detail = client.get(f"/api/appointments/{created['id']}").json()
    assert detail["status"] == "EXPIRED"
    assert [event["to_status"] for event in detail["events"]] == ["PENDING", "EXPIRED"]
    assert detail["events"][-1]["actor_role"] == "SYSTEM"


def test_database_rejects_overlapping_active_appointments(db, customer, provider_setup):
    from app.models import Appointment, AppointmentStatus

    start = future_slot(days=3, hour=10)
    first = Appointment(
        customer_id=customer.id,
        provider_id=provider_setup["profile"].id,
        service_id=provider_setup["service"].id,
        starts_at=start,
        ends_at=start + timedelta(minutes=60),
        duration_minutes=60,
        status=AppointmentStatus.PENDING.value,
    )
    db.add(first)
    db.commit()

    second = Appointment(
        customer_id=customer.id,
        provider_id=provider_setup["profile"].id,
        service_id=provider_setup["service"].id,
        starts_at=start + timedelta(minutes=30),
        ends_at=start + timedelta(minutes=90),
        duration_minutes=60,
        status=AppointmentStatus.CONFIRMED.value,
    )
    db.add(second)
    with pytest.raises(IntegrityError) as failure:
        db.commit()
    assert getattr(failure.value.orig, "sqlstate", None) == "23P01"
    db.rollback()


def test_concurrent_bookings_yield_exactly_one_success(db, provider_setup):
    from app.core.errors import AppError

    customers = [
        make_user(db, Role.CUSTOMER.value, f"race{i}@example.com") for i in range(2)
    ]
    emails = [c.email for c in customers]
    start = future_slot(days=4, hour=10)
    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def worker(email: str) -> None:
        session = SessionLocal()
        try:
            user = session.execute(select(User).where(User.email == email)).scalar_one()
            barrier.wait(timeout=10)
            try:
                create_booking(
                    session,
                    user,
                    provider_setup["profile"].id,
                    provider_setup["service"].id,
                    start,
                )
                outcome = "ok"
            except AppError as exc:
                outcome = exc.code
        finally:
            session.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(email,)) for email in emails]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(results) == ["SLOT_UNAVAILABLE", "ok"]

    with SessionLocal() as session:
        active = session.execute(
            text(
                "SELECT count(*) FROM appointments WHERE provider_id = :pid "
                "AND status IN ('PENDING','CONFIRMED')"
            ),
            {"pid": provider_setup["profile"].id},
        ).scalar_one()
    assert active == 1
