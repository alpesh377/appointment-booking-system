from __future__ import annotations

import re
from datetime import date as date_type, datetime, time, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    value = value.strip()
    if not EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def _validate_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("A timezone is required.")
    return value.astimezone(timezone.utc)


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=50)


class ProviderCreate(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=50)
    timezone: str = "UTC"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class ProviderUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    phone: str | None = Field(default=None, max_length=50)
    timezone: str | None = None


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=120)
    duration_minutes: int

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value < 15 or value > 480 or value % 5 != 0:
            raise ValueError("Duration must be between 15 and 480 minutes in steps of 5.")
        return value


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    duration_minutes: int | None = None
    is_active: bool | None = None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 15 or value > 480 or value % 5 != 0:
            raise ValueError("Duration must be between 15 and 480 minutes in steps of 5.")
        return value


class WindowInput(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @field_validator("end_time")
    @classmethod
    def order(cls, value: time, info):
        start = info.data.get("start_time")
        if start is not None and value <= start:
            raise ValueError("End time must be after start time.")
        return value


class WindowsUpdate(BaseModel):
    windows: list[WindowInput]


class BreakInput(BaseModel):
    weekday: int | None = Field(default=None, ge=0, le=6)
    date: date_type | None = None
    start_time: time
    end_time: time

    @field_validator("end_time")
    @classmethod
    def order(cls, value: time, info):
        start = info.data.get("start_time")
        if start is not None and value <= start:
            raise ValueError("End time must be after start time.")
        return value

    @field_validator("date")
    @classmethod
    def one_kind(cls, value: date_type | None, info):
        weekday = info.data.get("weekday")
        if (value is None) == (weekday is None):
            raise ValueError("Provide exactly one of weekday or date.")
        return value


class BreaksUpdate(BaseModel):
    breaks: list[BreakInput]


class OverrideInput(BaseModel):
    date: date_type
    is_closed: bool = False
    note: str | None = Field(default=None, max_length=300)
    windows: list[tuple[time, time]] = Field(default_factory=list)


class OverridesUpdate(BaseModel):
    overrides: list[OverrideInput]


class BookingCreate(BaseModel):
    provider_id: str
    service_id: str
    starts_at: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("starts_at")
    @classmethod
    def validate_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value)


class RescheduleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def validate_aware(cls, value: datetime) -> datetime:
        return _validate_aware(value)


class ReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ActiveRequest(BaseModel):
    active: bool


class StatusFilter(BaseModel):
    status: Literal[
        "PENDING",
        "CONFIRMED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED",
        "EXPIRED",
        "RESCHEDULED",
    ]
