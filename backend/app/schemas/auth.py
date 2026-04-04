from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, SecretStr, field_validator

from app.schemas.base import APIModel


class RegisterRequest(APIModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class LoginRequest(APIModel):
    email: EmailStr
    password: SecretStr


class RefreshTokenRequest(APIModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class UserRead(APIModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    created_at: datetime
    updated_at: datetime
    version: int


class AuthTokens(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class AuthSession(APIModel):
    user: UserRead
    tokens: AuthTokens
