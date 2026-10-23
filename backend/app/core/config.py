from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://abs:abs@localhost:5432/appointment_booking"
    app_origin: str = "http://localhost:3000"
    jwt_secret: str = "dev-only-secret"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 24
    cookie_secure: bool = False
    app_env: str = "development"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
