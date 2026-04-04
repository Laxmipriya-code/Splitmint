from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, HttpUrl, field_validator

from app.schemas.base import APIModel


class ParticipantCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=120)
    avatar_url: HttpUrl | None = None
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ParticipantUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: HttpUrl | None = None
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return " ".join(value.strip().split()) if value else value


class ParticipantRead(APIModel):
    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    avatar_url: str | None
    color_hex: str | None
    is_active: bool
    is_owner: bool
    created_at: datetime
    updated_at: datetime
    version: int
