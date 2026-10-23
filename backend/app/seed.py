from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Role, User


def main() -> int:
    email = (settings.admin_email or "").strip()
    password = settings.admin_password or ""
    if not email or not password:
        print(
            "ADMIN_EMAIL and ADMIN_PASSWORD must be set to create the first administrator.",
            file=sys.stderr,
        )
        return 1
    if len(password) < 8:
        print("ADMIN_PASSWORD must be at least 8 characters.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            if existing.role == Role.ADMIN.value:
                print(f"Administrator {email} already exists; nothing to do.")
                return 0
            print(f"An account with {email} exists but is not an administrator.", file=sys.stderr)
            return 1
        admin = User(
            email=email,
            password_hash=hash_password(password),
            role=Role.ADMIN.value,
            full_name=settings.admin_name,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Created administrator {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
