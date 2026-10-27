from __future__ import annotations

from datetime import timedelta

import pytest
from app.models import DateOverride, ProviderProfile, Service, User
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import utc_today


def test_email_uniqueness_is_case_insensitive(db, customer):
    db.add(
        User(
            email=customer.email.upper(),
            password_hash="irrelevant",
            role="CUSTOMER",
            full_name="Duplicate",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_one_provider_profile_per_account(db, provider_setup):
    db.add(
        ProviderProfile(
            user_id=provider_setup["user"].id,
            display_name="Second profile",
            category="General",
            timezone="UTC",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_service_duration_check_rejects_out_of_range_values(db, provider_setup):
    for duration in (14, 17, 485):
        db.add(
            Service(
                provider_id=provider_setup["profile"].id,
                name=f"Invalid {duration}",
                category="General",
                duration_minutes=duration,
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_one_override_per_provider_and_date(db, provider_setup):
    day = utc_today() + timedelta(days=6)
    db.add(DateOverride(provider_id=provider_setup["profile"].id, date=day, is_closed=True))
    db.commit()
    db.add(DateOverride(provider_id=provider_setup["profile"].id, date=day, is_closed=False))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_appointment_dashboard_indexes_exist(db):
    names = set(
        db.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'appointments'")).scalars()
    )
    assert {
        "ix_appointments_provider_start",
        "ix_appointments_customer_start",
        "ix_appointments_status",
    } <= names
