from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError, not_found
from app.models import Appointment, ProviderProfile, Role, User
from app.services import lifecycle
from app.services.serialization import appointment_payload, provider_payload, user_payload


def stats(db: Session) -> dict:
    customers = db.execute(
        select(func.count()).select_from(User).where(User.role == Role.CUSTOMER.value)
    ).scalar_one()
    providers = db.execute(select(func.count()).select_from(ProviderProfile)).scalar_one()
    appointments = db.execute(select(func.count()).select_from(Appointment)).scalar_one()
    rows = db.execute(select(Appointment.status, func.count()).group_by(Appointment.status)).all()
    by_status = dict(rows)
    return {
        "customers": customers,
        "providers": providers,
        "appointments": appointments,
        "by_status": by_status,
    }


def list_customers(db: Session, query: str | None = None) -> list[dict]:
    stmt = select(User).where(User.role == Role.CUSTOMER.value).order_by(User.full_name.asc())
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(User.full_name.ilike(pattern) | User.email.ilike(pattern))
    return [user_payload(u) for u in db.execute(stmt).scalars()]


def list_all_providers(db: Session) -> list[dict]:
    rows = db.execute(
        select(ProviderProfile)
        .options(selectinload(ProviderProfile.services), selectinload(ProviderProfile.user))
        .order_by(ProviderProfile.display_name.asc())
    ).scalars()
    return [provider_payload(provider, include_inactive=True) for provider in rows.unique()]


def set_user_active(db: Session, actor: User, user_id: uuid.UUID, active: bool) -> dict:
    target = db.get(User, user_id)
    if target is None:
        raise not_found("Account")
    if target.role == Role.PROVIDER.value:
        raise AppError(
            409,
            "USE_PROVIDER_ENDPOINT",
            "Deactivate providers through the provider management endpoint.",
        )
    if not active:
        if target.id == actor.id:
            raise AppError(403, "SELF_DEACTIVATION", "You cannot deactivate your own account.")
        if target.role == Role.ADMIN.value:
            remaining = db.execute(
                select(func.count())
                .select_from(User)
                .where(
                    User.role == Role.ADMIN.value,
                    User.is_active.is_(True),
                    User.id != target.id,
                )
            ).scalar_one()
            if remaining == 0:
                raise AppError(
                    403,
                    "LAST_ADMIN",
                    "The last active administrator cannot be deactivated.",
                )
    target.is_active = active
    db.commit()
    db.refresh(target)
    return user_payload(target)


def appointments_page(
    db: Session,
    actor: User,
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    provider_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = lifecycle.appointment_statement(
        actor,
        status=status,
        date_from=date_from,
        date_to=date_to,
        provider_id=provider_id,
        customer_id=customer_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars()
    return {
        "items": [appointment_payload(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
