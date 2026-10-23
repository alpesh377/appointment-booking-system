from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import forbidden, unauthenticated
from app.core.security import decode_access_token
from app.db import get_db
from app.models import ProviderProfile, Role, User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise unauthenticated()
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise unauthenticated("Your session has expired.")
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError:
        raise unauthenticated("Your session is invalid.") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthenticated("This account is not active.")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden()
        return user

    return dependency


def require_customer(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.CUSTOMER.value:
        raise forbidden()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.ADMIN.value:
        raise forbidden()
    return user


def require_provider(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.PROVIDER.value or user.provider_profile is None:
        raise forbidden()
    return user


def provider_profile(user: User) -> ProviderProfile:
    profile = user.provider_profile
    if profile is None:
        raise forbidden()
    return profile
