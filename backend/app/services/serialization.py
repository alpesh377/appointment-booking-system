from __future__ import annotations

from datetime import datetime

from app.models import (
    Appointment,
    AppointmentEvent,
    ProviderProfile,
    Service,
    User,
)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def service_payload(service: Service) -> dict:
    return {
        "id": str(service.id),
        "provider_id": str(service.provider_id),
        "name": service.name,
        "category": service.category,
        "duration_minutes": service.duration_minutes,
        "is_active": service.is_active,
    }


def provider_summary(provider: ProviderProfile) -> dict:
    active_durations = sorted(
        {s.duration_minutes for s in provider.services if s.is_active}
    )
    return {
        "id": str(provider.id),
        "display_name": provider.display_name,
        "category": provider.category,
        "timezone": provider.timezone,
        "is_active": provider.is_active,
        "durations": active_durations,
    }


def provider_payload(provider: ProviderProfile, include_inactive: bool = False) -> dict:
    services = [s for s in provider.services if include_inactive or s.is_active]
    services.sort(key=lambda s: s.name.lower())
    return {
        **provider_summary(provider),
        "bio": provider.bio,
        "user_id": str(provider.user_id),
        "full_name": provider.user.full_name if provider.user else None,
        "email": provider.user.email if provider.user else None,
        "phone": provider.user.phone if provider.user else None,
        "services": [service_payload(s) for s in services],
    }


def user_payload(user: User) -> dict:
    payload = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "created_at": iso(user.created_at),
    }
    if user.provider_profile is not None:
        payload["provider_id"] = str(user.provider_profile.id)
    return payload


def event_payload(event: AppointmentEvent) -> dict:
    return {
        "id": str(event.id),
        "from_status": event.from_status,
        "to_status": event.to_status,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "actor_role": event.actor_role,
        "reason": event.reason,
        "created_at": iso(event.created_at),
    }


def appointment_payload(
    appointment: Appointment,
    events: list[AppointmentEvent] | None = None,
) -> dict:
    provider = appointment.provider
    service = appointment.service
    customer = appointment.customer
    payload = {
        "id": str(appointment.id),
        "status": appointment.status,
        "starts_at": iso(appointment.starts_at),
        "ends_at": iso(appointment.ends_at),
        "duration_minutes": appointment.duration_minutes,
        "notes": appointment.notes,
        "hold_expires_at": iso(appointment.hold_expires_at),
        "rescheduled_from_id": (
            str(appointment.rescheduled_from_id) if appointment.rescheduled_from_id else None
        ),
        "rescheduled_to_id": (
            str(appointment.rescheduled_to_id) if appointment.rescheduled_to_id else None
        ),
        "cancelled_by_role": appointment.cancelled_by_role,
        "cancellation_reason": appointment.cancellation_reason,
        "created_at": iso(appointment.created_at),
        "provider": {
            "id": str(provider.id),
            "display_name": provider.display_name,
            "category": provider.category,
            "timezone": provider.timezone,
        },
        "service": {
            "id": str(service.id),
            "name": service.name,
            "category": service.category,
            "duration_minutes": service.duration_minutes,
        },
        "customer": {
            "id": str(customer.id),
            "full_name": customer.full_name,
            "email": customer.email,
        },
    }
    if events is not None:
        payload["events"] = [event_payload(e) for e in events]
    return payload
