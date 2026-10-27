from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder used only for local development; production refuses to start with it.
DEV_JWT_PLACEHOLDER = "dev-only-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://abs:abs@localhost:5432/appointment_booking"
    app_origin: str = "http://localhost:3000"
    jwt_secret: str = DEV_JWT_PLACEHOLDER
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 24
    cookie_secure: bool = False
    app_env: str = "development"
    log_level: str = "INFO"

    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"

    lock_timeout_ms: int = 5000
    scheduling_horizon_days: int = 30
    booking_notice_hours: int = 2
    pending_hold_hours: int = 24

    admin_email: str | None = None
    admin_password: str | None = None
    admin_name: str = "Administrator"

    @property
    def cookie_name(self) -> str:
        return "__Host-session" if self.cookie_secure else "session"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def _reject_unsafe_defaults(self) -> "Settings":
        """Fail fast instead of serving production traffic with development secrets."""
        if not self.is_production:
            return self
        if self.jwt_secret == DEV_JWT_PLACEHOLDER or len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be set to a long random value in production.")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
