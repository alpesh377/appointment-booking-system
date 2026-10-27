from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, forbidden, not_found
from app.core.security import MIN_PASSWORD_LENGTH, hash_password
from app.db import violated_constraint
from app.models import ProviderProfile, Role, Service, User
from app.services.availability import get_provider
from app.services.serialization import provider_payload, provider_summary


def _validate_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise AppError(
            422, "VALIDATION_ERROR", "Unknown timezone.", {"timezone": "Unknown timezone."}
        ) from None
    return name


def list_providers(db: Session, query: str | None = None) -> list[dict]:
    stmt = (
        select(ProviderProfile)
        .options(selectinload(ProviderProfile.services), selectinload(ProviderProfile.user))
        .where(ProviderProfile.is_active.is_(True))
    )
    if query:
        pattern = f"%{query.strip()}%"
        matching_service_providers = select(Service.provider_id).where(
            Service.is_active.is_(True), Service.category.ilike(pattern)
        )
        stmt = stmt.where(
            or_(
                ProviderProfile.display_name.ilike(pattern),
                ProviderProfile.id.in_(matching_service_providers),
            )
        )
    stmt = stmt.order_by(ProviderProfile.display_name.asc())
    return [provider_summary(p) for p in db.execute(stmt).scalars().unique()]


def get_provider_detail(db: Session, provider_id: uuid.UUID) -> dict:
    provider = db.execute(
        select(ProviderProfile)
        .options(selectinload(ProviderProfile.services), selectinload(ProviderProfile.user))
        .where(ProviderProfile.id == provider_id)
    ).scalar_one_or_none()
    if provider is None or not provider.is_active:
        raise not_found("Provider")
    return provider_payload(provider)


def create_provider(db: Session, payload: dict) -> dict:
    email = payload["email"].strip()
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise AppError(409, "EMAIL_TAKEN", "An account with that email already exists.")
    if len(payload["password"]) < MIN_PASSWORD_LENGTH:
        raise AppError(
            422,
            "VALIDATION_ERROR",
            "Password is too short.",
            {"password": f"Use at least {MIN_PASSWORD_LENGTH} characters."},
        )
    timezone_name = _validate_timezone(payload.get("timezone") or "UTC")
    user = User(
        email=email,
        password_hash=hash_password(payload["password"]),
        role=Role.PROVIDER.value,
        full_name=payload["full_name"].strip(),
        phone=payload.get("phone"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    provider = ProviderProfile(
        user_id=user.id,
        display_name=payload["display_name"].strip(),
        category=payload["category"].strip(),
        bio=payload.get("bio"),
        timezone=timezone_name,
        is_active=True,
    )
    db.add(provider)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # The unique email index rejected a concurrent creation with the same address.
        if violated_constraint(exc) != "users_email_key":
            raise
        raise AppError(409, "EMAIL_TAKEN", "An account with that email already exists.") from None
    db.refresh(provider)
    provider.user = user
    provider.services = []
    return provider_payload(provider)


def _apply_profile(payload: dict, provider: ProviderProfile) -> None:
    if "display_name" in payload and payload["display_name"] is not None:
        provider.display_name = payload["display_name"].strip()
    if "category" in payload and payload["category"] is not None:
        provider.category = payload["category"].strip()
    if "bio" in payload:
        provider.bio = payload["bio"]
    if payload.get("timezone") is not None:
        provider.timezone = _validate_timezone(payload["timezone"])
    if payload.get("phone") is not None and provider.user is not None:
        provider.user.phone = payload["phone"]


def update_provider(db: Session, user: User, provider_id: uuid.UUID, payload: dict) -> dict:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise not_found("Provider")
    if user.role != Role.ADMIN.value and not (
        user.provider_profile is not None and user.provider_profile.id == provider.id
    ):
        raise forbidden()
    _apply_profile(payload, provider)
    db.commit()
    db.refresh(provider)
    return provider_payload(provider)


def set_provider_active(db: Session, provider_id: uuid.UUID, active: bool) -> dict:
    provider = db.get(ProviderProfile, provider_id)
    if provider is None:
        raise not_found("Provider")
    provider.is_active = active
    provider.user.is_active = active
    db.commit()
    db.refresh(provider)
    return provider_payload(provider)


def create_service(db: Session, user: User, provider_id: uuid.UUID, payload: dict) -> dict:
    provider = get_provider(db, provider_id)
    if user.provider_profile is None or user.provider_profile.id != provider.id:
        raise forbidden()
    service = Service(
        provider_id=provider.id,
        name=payload["name"].strip(),
        category=payload["category"].strip(),
        duration_minutes=payload["duration_minutes"],
        is_active=True,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return {
        "id": str(service.id),
        "name": service.name,
        "category": service.category,
        "duration_minutes": service.duration_minutes,
        "is_active": service.is_active,
        "provider_id": str(service.provider_id),
    }


def update_service(db: Session, user: User, service_id: uuid.UUID, payload: dict) -> dict:
    service = db.get(Service, service_id)
    if service is None:
        raise not_found("Service")
    if user.provider_profile is None or user.provider_profile.id != service.provider_id:
        raise forbidden()
    if payload.get("name") is not None:
        service.name = payload["name"].strip()
    if payload.get("category") is not None:
        service.category = payload["category"].strip()
    if payload.get("duration_minutes") is not None:
        service.duration_minutes = payload["duration_minutes"]
    if payload.get("is_active") is not None:
        service.is_active = payload["is_active"]
    db.commit()
    db.refresh(service)
    return {
        "id": str(service.id),
        "name": service.name,
        "category": service.category,
        "duration_minutes": service.duration_minutes,
        "is_active": service.is_active,
        "provider_id": str(service.provider_id),
    }


def deactivate_service(db: Session, user: User, service_id: uuid.UUID) -> dict:
    return update_service(db, user, service_id, {"is_active": False})
