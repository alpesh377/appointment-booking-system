from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Domain error carrying an HTTP status and a stable machine code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields


def error_payload(code: str, message: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if fields:
        payload["fields"] = fields
    return payload


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(exc.code, exc.message, exc.fields),
    )


class ValidationFailure(AppError):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(422, "VALIDATION_ERROR", "The submitted data is invalid.", fields)


def not_found(what: str = "Resource") -> AppError:
    return AppError(404, "NOT_FOUND", f"{what} was not found.")


def forbidden(message: str = "You are not permitted to perform this action.") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def unauthenticated(message: str = "Authentication is required.") -> AppError:
    return AppError(401, "UNAUTHENTICATED", message)


def conflict(code: str, message: str) -> AppError:
    return AppError(409, code, message)
