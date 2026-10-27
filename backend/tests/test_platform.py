from __future__ import annotations

import os
import subprocess
import sys

import pytest
from app.core.config import Settings, settings
from app.main import app
from app.seed import main as seed_main
from pydantic import ValidationError
from sqlalchemy import text

from tests.conftest import login

MIGRATION_URL = "postgresql+psycopg://abs:abs@localhost:5432/appointment_booking_migration_test"


def test_openapi_documents_every_area():
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/auth/login" in paths
    assert "/api/providers" in paths
    assert "/api/availability" in paths
    assert "/api/appointments" in paths
    assert "/api/dashboard/provider" in paths
    assert "/api/admin/appointments" in paths
    assert "CSRF" in schema["info"]["description"]


def test_seed_creates_one_admin_and_is_idempotent(db):
    assert seed_main() == 0
    assert seed_main() == 0
    with db.begin():
        count = db.execute(text("SELECT count(*) FROM users WHERE role = 'ADMIN'")).scalar_one()
    assert count == 1


def test_seed_fails_without_credentials(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", None)
    assert seed_main() == 1


def test_admin_seeded_account_can_sign_in(client, db):
    assert seed_main() == 0
    response = login(client, settings.admin_email, settings.admin_password)
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_migrations_apply_and_reverse_cleanly():
    import psycopg

    admin_dsn = "postgresql://abs:abs@localhost:5432/postgres"
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'appointment_booking_migration_test'"
        ).fetchone()
        if not exists:
            connection.execute("CREATE DATABASE appointment_booking_migration_test")

    env = {**os.environ, "DATABASE_URL": MIGRATION_URL}
    backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for args in (["upgrade", "head"], ["downgrade", "base"], ["upgrade", "head"]):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=backend,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    from sqlalchemy import create_engine

    engine = create_engine(MIGRATION_URL)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        }
    engine.dispose()
    assert {"users", "provider_profiles", "services", "appointments", "appointment_events"} <= tables


def test_production_settings_reject_development_defaults():
    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="dev-only-secret", cookie_secure=False)

    with pytest.raises(ValidationError):
        Settings(app_env="production", jwt_secret="x" * 40, cookie_secure=False)

    safe = Settings(app_env="production", jwt_secret="x" * 40, cookie_secure=True)
    assert safe.is_production
