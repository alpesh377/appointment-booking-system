from __future__ import annotations

import os
from datetime import UTC, date, datetime, time, timedelta

os.environ["DATABASE_URL"] = "postgresql+psycopg://abs:abs@localhost:5432/appointment_booking_test"
os.environ["APP_ORIGIN"] = "http://testserver"
os.environ["JWT_SECRET"] = "test-secret-value-that-is-long-enough-for-hs256"
os.environ["COOKIE_SECURE"] = "false"
os.environ["ADMIN_EMAIL"] = "admin@example.com"
os.environ["ADMIN_PASSWORD"] = "admin-password-123"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db import SessionLocal, engine
from app.main import app
from app.models import Base, ProviderProfile, Role, User

TEST_ORIGIN = "http://testserver"
DEFAULT_PASSWORD = "password123"
TRUNCATE = (
    "TRUNCATE appointment_events, appointments, date_override_windows, date_overrides, "
    "schedule_breaks, availability_rules, services, provider_profiles, users "
    "RESTART IDENTITY CASCADE"
)


@pytest.fixture(scope="session", autouse=True)
def schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE appointments ADD CONSTRAINT appointments_no_overlap "
                "EXCLUDE USING gist (provider_id WITH =, "
                "tstzrange(starts_at, ends_at, '[)') WITH &&) "
                "WHERE (status IN ('PENDING','CONFIRMED'))"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_appointment_one_successor "
                "ON appointments (rescheduled_from_id) WHERE rescheduled_from_id IS NOT NULL"
            )
        )
    yield


@pytest.fixture(autouse=True)
def clean_db(schema):
    with engine.begin() as conn:
        conn.execute(text(TRUNCATE))
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.get("/api/health")
        yield test_client


def csrf_headers(client: TestClient) -> dict[str, str]:
    return {
        "Origin": TEST_ORIGIN,
        "X-CSRF-Token": client.cookies.get("csrf_token", ""),
    }


def post(client: TestClient, url: str, **kwargs):
    headers = {**kwargs.pop("headers", {}), **csrf_headers(client)}
    return client.post(url, headers=headers, **kwargs)


def patch(client: TestClient, url: str, **kwargs):
    headers = {**kwargs.pop("headers", {}), **csrf_headers(client)}
    return client.patch(url, headers=headers, **kwargs)


def put(client: TestClient, url: str, **kwargs):
    headers = {**kwargs.pop("headers", {}), **csrf_headers(client)}
    return client.put(url, headers=headers, **kwargs)


def delete(client: TestClient, url: str, **kwargs):
    headers = {**kwargs.pop("headers", {}), **csrf_headers(client)}
    return client.delete(url, headers=headers, **kwargs)


def make_user(
    db,
    role: str,
    email: str,
    *,
    name: str | None = None,
    password: str = DEFAULT_PASSWORD,
    active: bool = True,
    timezone_name: str = "UTC",
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=name or email.split("@")[0].title(),
        is_active=active,
    )
    db.add(user)
    db.flush()
    if role == Role.PROVIDER.value:
        db.add(
            ProviderProfile(
                user_id=user.id,
                display_name=name or "Provider",
                category="General",
                timezone=timezone_name,
                is_active=active,
            )
        )
    db.commit()
    db.refresh(user)
    return user


def login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    return post(client, "/api/auth/login", json={"email": email, "password": password})


def future_slot(days: int = 3, hour: int = 10, minute: int = 0) -> datetime:
    target = datetime.now(UTC).date() + timedelta(days=days)
    return datetime.combine(target, time(hour, minute), tzinfo=UTC)


def utc_today() -> date:
    return datetime.now(UTC).date()


@pytest.fixture
def customer(db):
    return make_user(db, Role.CUSTOMER.value, "customer@example.com", name="Casey Customer")


@pytest.fixture
def provider_setup(db):
    from app.models import AvailabilityRule, Service

    user = make_user(db, Role.PROVIDER.value, "provider@example.com", name="Pat Provider")
    profile = user.provider_profile
    for weekday in range(7):
        db.add(
            AvailabilityRule(
                provider_id=profile.id,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        )
    service = Service(
        provider_id=profile.id,
        name="Consultation",
        category="General",
        duration_minutes=60,
    )
    db.add(service)
    db.commit()
    db.refresh(profile)
    db.refresh(service)
    return {"user": user, "profile": profile, "service": service}
