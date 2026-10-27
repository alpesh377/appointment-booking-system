from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_customer
from app.core.errors import AppError
from app.db import get_db
from app.models import AppointmentStatus, User
from app.schemas import BookingCreate, ReasonRequest, RescheduleRequest
from app.services import booking as booking_service
from app.services import lifecycle

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _uuid(value: str, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise AppError(
            422, "VALIDATION_ERROR", "Invalid identifier.", {field: "Invalid identifier."}
        ) from None


@router.post("", status_code=201, summary="Book an appointment")
def create_appointment(
    payload: BookingCreate,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> dict:
    return booking_service.create_booking(
        db,
        customer,
        _uuid(payload.provider_id, "provider_id"),
        _uuid(payload.service_id, "service_id"),
        payload.starts_at,
        payload.notes,
    )


@router.get("", summary="List appointments for the current role")
def list_appointments(
    status: AppointmentStatus | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    view: Literal["upcoming", "past", "cancelled"] | None = Query(default=None),
    provider_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    return lifecycle.list_appointments(
        db,
        user,
        status=status.value if status else None,
        date_from=date_from,
        date_to=date_to,
        view=view,
        provider_id=provider_id,
        customer_id=customer_id,
    )


@router.get("/{appointment_id}", summary="Appointment detail and history")
def appointment_detail(
    appointment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return lifecycle.detail(db, user, appointment_id)


@router.post("/{appointment_id}/confirm", summary="Confirm a pending request")
def confirm(
    appointment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return lifecycle.confirm(db, user, appointment_id)


@router.post("/{appointment_id}/reject", summary="Reject a pending request")
def reject(
    appointment_id: uuid.UUID,
    payload: ReasonRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return lifecycle.reject(db, user, appointment_id, payload.reason if payload else None)


@router.post("/{appointment_id}/cancel", summary="Cancel an appointment")
def cancel(
    appointment_id: uuid.UUID,
    payload: ReasonRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return lifecycle.cancel(db, user, appointment_id, payload.reason if payload else None)


@router.post("/{appointment_id}/complete", summary="Complete a confirmed appointment")
def complete(
    appointment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return lifecycle.complete(db, user, appointment_id)


@router.post("/{appointment_id}/reschedule", summary="Reschedule to a new time")
def reschedule(
    appointment_id: uuid.UUID,
    payload: RescheduleRequest,
    customer: User = Depends(require_customer),
    db: Session = Depends(get_db),
) -> dict:
    appointment = lifecycle.get_visible(db, customer, appointment_id)
    return booking_service.reschedule(db, customer, appointment, payload.starts_at)
