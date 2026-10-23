from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db import get_db
from app.models import User
from app.schemas import ReasonRequest
from app.services import admin as admin_service
from app.services import lifecycle

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/stats", summary="Platform totals and statistics")
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return admin_service.stats(db)


@router.get("/customers", summary="List customer accounts")
def customers(
    q: str | None = Query(default=None),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    return admin_service.list_customers(db, q)


@router.get("/providers", summary="List all providers, including inactive")
def providers(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    return admin_service.list_all_providers(db)


@router.post("/users/{user_id}/deactivate", summary="Deactivate an account")
def deactivate_user(
    user_id: uuid.UUID,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return admin_service.set_user_active(db, actor, user_id, False)


@router.post("/users/{user_id}/reactivate", summary="Reactivate an account")
def reactivate_user(
    user_id: uuid.UUID,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return admin_service.set_user_active(db, actor, user_id, True)


@router.get("/appointments", summary="All appointments with filters")
def appointments(
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    provider_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return admin_service.appointments_page(
        db,
        actor,
        status=status,
        date_from=date_from,
        date_to=date_to,
        provider_id=provider_id,
        customer_id=customer_id,
        page=page,
        page_size=page_size,
    )


@router.post("/appointments/{appointment_id}/cancel", summary="Supervisory cancellation")
def cancel_appointment(
    appointment_id: uuid.UUID,
    payload: ReasonRequest | None = None,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return lifecycle.cancel(db, actor, appointment_id, payload.reason if payload else None)
