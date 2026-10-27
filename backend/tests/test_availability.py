from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from app.models import Role

from tests.conftest import login, make_user, patch, post, put, utc_today


def _slot_count(client, provider_id, service_id, day):
    response = client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_id),
            "service_id": str(service_id),
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    return len(response.json()["slots"])


def test_slots_are_generated_for_the_service_duration(client, provider_setup):
    day = utc_today() + timedelta(days=3)
    assert _slot_count(client, provider_setup["profile"].id, provider_setup["service"].id, day) == 8


def test_different_service_durations_produce_different_grids(client, provider_setup):
    login(client, provider_setup["user"].email)
    created = post(
        client,
        f"/api/providers/{provider_setup['profile'].id}/services",
        json={"name": "Quick", "category": "General", "duration_minutes": 30},
    )
    assert created.status_code == 201
    day = utc_today() + timedelta(days=3)
    assert _slot_count(client, provider_setup["profile"].id, provider_setup["service"].id, day) == 8
    assert _slot_count(client, provider_setup["profile"].id, created.json()["id"], day) == 16


def test_service_must_belong_to_the_provider(client, db, provider_setup):
    from app.models import Service

    other = make_user(db, Role.PROVIDER.value, "other@example.com", name="Other")
    other_service = Service(
        provider_id=other.provider_profile.id,
        name="Other",
        category="Other",
        duration_minutes=30,
    )
    db.add(other_service)
    db.commit()
    day = utc_today() + timedelta(days=3)
    response = client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(other_service.id),
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
        },
    )
    assert response.status_code == 404


def test_service_is_required(client, provider_setup):
    day = utc_today() + timedelta(days=3)
    response = client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_setup["profile"].id),
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
        },
    )
    assert response.status_code == 422


def test_provider_replaces_windows_and_slots_follow(client, provider_setup):
    day = utc_today() + timedelta(days=3)
    login(client, provider_setup["user"].email)
    response = put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/windows",
        json={"windows": [{"weekday": day.weekday(), "start_time": "10:00", "end_time": "12:00"}]},
    )
    assert response.status_code == 200
    assert _slot_count(client, provider_setup["profile"].id, provider_setup["service"].id, day) == 2


def test_overlapping_windows_are_rejected(client, provider_setup):
    login(client, provider_setup["user"].email)
    response = put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/windows",
        json={
            "windows": [
                {"weekday": 0, "start_time": "09:00", "end_time": "12:00"},
                {"weekday": 0, "start_time": "11:00", "end_time": "13:00"},
            ]
        },
    )
    assert response.status_code == 422


def test_closed_override_removes_the_day(client, provider_setup):
    day = utc_today() + timedelta(days=3)
    login(client, provider_setup["user"].email)
    response = put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/overrides",
        json={"overrides": [{"date": day.isoformat(), "is_closed": True}]},
    )
    assert response.status_code == 200
    assert _slot_count(client, provider_setup["profile"].id, provider_setup["service"].id, day) == 0


def test_past_availability_edits_are_rejected(client, provider_setup):
    login(client, provider_setup["user"].email)
    past = (utc_today() - timedelta(days=1)).isoformat()
    break_response = put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/breaks",
        json={"breaks": [{"date": past, "start_time": "12:00", "end_time": "13:00"}]},
    )
    assert break_response.status_code == 422
    override_response = put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/overrides",
        json={"overrides": [{"date": past, "is_closed": True}]},
    )
    assert override_response.status_code == 422


def test_another_provider_cannot_edit_availability(client, db, provider_setup):
    other = make_user(db, Role.PROVIDER.value, "other2@example.com", name="Other")
    login(client, other.email)
    response = put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/windows",
        json={"windows": []},
    )
    assert response.status_code == 403


def test_horizon_hides_distant_dates(client, provider_setup):
    far = utc_today() + timedelta(days=31)
    assert _slot_count(client, provider_setup["profile"].id, provider_setup["service"].id, far) == 0


def test_timezone_change_moves_future_slots_not_existing_appointments(client, db, provider_setup):
    customer = make_user(db, Role.CUSTOMER.value, "tz@example.com")
    login(client, customer.email)
    day = utc_today() + timedelta(days=3)
    starts_at = datetime.combine(day, time(10, 0), tzinfo=UTC)
    booked = post(
        client,
        "/api/appointments",
        json={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "starts_at": starts_at.isoformat(),
        },
    )
    assert booked.status_code == 201, booked.text
    original_instant = datetime.fromisoformat(booked.json()["starts_at"])

    before = client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
        },
    ).json()["slots"]

    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)
    changed = patch(
        client,
        f"/api/providers/{provider_setup['profile'].id}",
        json={"timezone": "Europe/Berlin"},
    )
    assert changed.status_code == 200, changed.text

    after = client.get(
        "/api/availability",
        params={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "date_from": day.isoformat(),
            "date_to": day.isoformat(),
        },
    ).json()["slots"]

    detail = client.get(f"/api/appointments/{booked.json()['id']}")
    assert detail.status_code == 200, detail.text
    assert datetime.fromisoformat(detail.json()["starts_at"]) == original_instant
    assert before != after
    assert before[0] != after[0]


def test_conflicts_are_surfaced_after_hours_are_shortened(client, db, provider_setup):
    customer = make_user(db, Role.CUSTOMER.value, "conflict@example.com")
    login(client, customer.email)
    day = utc_today() + timedelta(days=3)
    starts_at = datetime.combine(day, time(10, 0), tzinfo=UTC)
    booked = post(
        client,
        "/api/appointments",
        json={
            "provider_id": str(provider_setup["profile"].id),
            "service_id": str(provider_setup["service"].id),
            "starts_at": starts_at.isoformat(),
        },
    )
    assert booked.status_code == 201, booked.text

    post(client, "/api/auth/logout")
    login(client, provider_setup["user"].email)
    put(
        client,
        f"/api/providers/{provider_setup['profile'].id}/availability/windows",
        json={"windows": [{"weekday": day.weekday(), "start_time": "09:00", "end_time": "09:30"}]},
    )
    conflicts = client.get(f"/api/providers/{provider_setup['profile'].id}/availability/conflicts")
    assert conflicts.status_code == 200
    assert [item["id"] for item in conflicts.json()] == [booked.json()["id"]]


def test_typed_availability_payloads_reject_invalid_shapes(client, provider_setup):
    login(client, "provider@example.com")
    path = f"/api/providers/{provider_setup['profile'].id}/availability"

    out_of_range = put(
        client,
        f"{path}/windows",
        json={"windows": [{"weekday": 9, "start_time": "10:00", "end_time": "11:00"}]},
    )
    assert out_of_range.status_code == 422

    reversed_window = put(
        client,
        f"{path}/windows",
        json={"windows": [{"weekday": 0, "start_time": "11:00", "end_time": "10:00"}]},
    )
    assert reversed_window.status_code == 422

    both_break_kinds = put(
        client,
        f"{path}/breaks",
        json={
            "breaks": [
                {
                    "weekday": 0,
                    "date": utc_today().isoformat(),
                    "start_time": "12:00",
                    "end_time": "13:00",
                }
            ]
        },
    )
    assert both_break_kinds.status_code == 422

    reversed_override = put(
        client,
        f"{path}/overrides",
        json={
            "overrides": [
                {
                    "date": (utc_today() + timedelta(days=2)).isoformat(),
                    "is_closed": False,
                    "windows": [{"start_time": "15:00", "end_time": "14:00"}],
                }
            ]
        },
    )
    assert reversed_override.status_code == 422
