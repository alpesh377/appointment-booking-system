from __future__ import annotations

from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.security import constant_time_equals, new_csrf_token

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def _origin_from_referer(referer: str) -> str | None:
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalise(origin: str) -> str:
    return origin.strip().rstrip("/").lower()


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            if settings.csrf_cookie_name not in request.cookies:
                response.set_cookie(
                    settings.csrf_cookie_name,
                    new_csrf_token(),
                    httponly=False,
                    samesite="lax",
                    secure=settings.cookie_secure,
                    path="/",
                )
            return response

        supplied_origin = request.headers.get("origin")
        if supplied_origin is None:
            referer = request.headers.get("referer")
            supplied_origin = _origin_from_referer(referer) if referer else None
        if supplied_origin is None or _normalise(supplied_origin) != _normalise(settings.app_origin):
            return JSONResponse(
                status_code=403,
                content={
                    "code": "CSRF_ORIGIN_MISMATCH",
                    "message": "The request origin could not be verified.",
                },
            )

        cookie_token = request.cookies.get(settings.csrf_cookie_name)
        header_token = request.headers.get(settings.csrf_header_name)
        if not cookie_token or not header_token or not constant_time_equals(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={
                    "code": "CSRF_TOKEN_INVALID",
                    "message": "The request could not be verified.",
                },
            )

        return await call_next(request)
