from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import admin, appointments, auth, availability, dashboards, providers
from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.errors import AppError, app_error_handler, error_payload
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger("app.api")

app = FastAPI(
    title="Appointment Booking System API",
    version="1.0.0",
    description=(
        "Slot generation, booking, appointment lifecycle and administration. "
        "All state-changing requests require the CSRF cookie echoed in the X-CSRF-Token header "
        "and a matching Origin."
    ),
)

app.add_middleware(CSRFMiddleware)
app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part not in {"body", "query", "path"}]
        field = ".".join(location) or "request"
        fields.setdefault(field, error.get("msg", "Invalid value."))
    return JSONResponse(
        status_code=422,
        content=error_payload("VALIDATION_ERROR", "The submitted data is invalid.", fields),
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_payload("INTERNAL_ERROR", "An unexpected error occurred."),
    )


@app.get("/api/health", tags=["system"], summary="Health check")
def health() -> dict:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health", include_in_schema=False)
def health_alias() -> dict:
    """Bare-path alias for probes and platforms that hardcode `/health`."""
    return health()


app.include_router(auth.router, prefix="/api")
app.include_router(providers.router, prefix="/api")
app.include_router(availability.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(dashboards.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
