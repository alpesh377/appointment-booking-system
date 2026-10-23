from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.db import get_db
from app.models import Role, User
from app.schemas import LoginRequest, ProfileUpdate, RegisterRequest
from app.services.serialization import user_payload

router = APIRouter(prefix="/auth", tags=["authentication"])


def _set_session(response: Response, user: User) -> None:
    token = create_access_token(str(user.id), user.role)
    response.set_cookie(
        settings.cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
        max_age=settings.jwt_ttl_minutes * 60,
    )


def _clear_session(response: Response) -> None:
    response.delete_cookie(settings.cookie_name, path="/")


@router.post("/register", summary="Register a customer account")
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    email = payload.email
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise AppError(409, "EMAIL_TAKEN", "An account with that email already exists.")
    full_name = payload.full_name or email.split("@")[0]
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=Role.CUSTOMER.value,
        full_name=full_name,
        phone=payload.phone,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _set_session(response, user)
    return user_payload(user)


@router.post("/login", summary="Sign in")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(401, "INVALID_CREDENTIALS", "The email or password is incorrect.")
    if not user.is_active:
        raise AppError(403, "ACCOUNT_INACTIVE", "This account is not active.")
    _set_session(response, user)
    return user_payload(user)


@router.post("/logout", summary="Sign out")
def logout(response: Response) -> dict:
    _clear_session(response)
    return {"ok": True}


@router.get("/me", summary="Current account")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_payload(user)


@router.patch("/me", summary="Update own profile")
def update_me(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        user.phone = payload.phone
    db.commit()
    db.refresh(user)
    return user_payload(user)
