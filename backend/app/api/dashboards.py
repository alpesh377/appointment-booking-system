from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_customer, require_provider
from app.db import get_db
from app.models import User
from app.services import admin as admin_service
from app.services import lifecycle

router = APIRouter(prefix="/dashboard", tags=["dashboards"])


@router.get("/customer", summary="Customer dashboard")
def customer_dashboard(user: User = Depends(require_customer), db: Session = Depends(get_db)) -> dict:
    return lifecycle.customer_dashboard(db, user)


@router.get("/provider", summary="Provider dashboard")
def provider_dashboard(user: User = Depends(require_provider), db: Session = Depends(get_db)) -> dict:
    return lifecycle.provider_dashboard(db, user)


@router.get("/admin", summary="Admin dashboard")
def admin_dashboard(user: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return admin_service.stats(db)
