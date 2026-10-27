from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_provider
from app.db import get_db
from app.models import User
from app.schemas import ProviderCreate, ProviderUpdate, ServiceCreate, ServiceUpdate
from app.services import providers as provider_service
from app.services.serialization import service_payload

router = APIRouter(tags=["providers"])


@router.get("/providers", summary="List active providers")
def list_providers(q: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[dict]:
    return provider_service.list_providers(db, q)


@router.get("/providers/{provider_id}", summary="Provider detail")
def provider_detail(provider_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    return provider_service.get_provider_detail(db, provider_id)


@router.post("/providers", status_code=201, summary="Create a provider account")
def create_provider(
    payload: ProviderCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.create_provider(db, payload.model_dump())


@router.patch("/providers/{provider_id}", summary="Update provider profile")
def update_provider(
    provider_id: uuid.UUID,
    payload: ProviderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.update_provider(db, user, provider_id, payload.model_dump(exclude_unset=True))


@router.post("/providers/{provider_id}/deactivate", summary="Deactivate a provider")
def deactivate_provider(
    provider_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.set_provider_active(db, provider_id, False)


@router.post("/providers/{provider_id}/reactivate", summary="Reactivate a provider")
def reactivate_provider(
    provider_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.set_provider_active(db, provider_id, True)


@router.get("/providers/{provider_id}/services", summary="Services offered by a provider")
def list_services(provider_id: uuid.UUID, db: Session = Depends(get_db)) -> list[dict]:
    provider = provider_service.get_provider_detail(db, provider_id)
    return provider["services"]


@router.get("/provider/services", summary="Own services, including inactive")
def own_services(
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> list[dict]:
    profile = user.provider_profile
    return [
        service_payload(service) for service in sorted(profile.services, key=lambda item: item.name.lower())
    ]


@router.post("/providers/{provider_id}/services", status_code=201, summary="Add a service")
def create_service(
    provider_id: uuid.UUID,
    payload: ServiceCreate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.create_service(db, user, provider_id, payload.model_dump())


@router.patch("/services/{service_id}", summary="Update a service")
def update_service(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.update_service(db, user, service_id, payload.model_dump(exclude_unset=True))


@router.post("/services/{service_id}/deactivate", summary="Deactivate a service")
def deactivate_service(
    service_id: uuid.UUID,
    user: User = Depends(require_provider),
    db: Session = Depends(get_db),
) -> dict:
    return provider_service.deactivate_service(db, user, service_id)
