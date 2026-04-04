from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _b64(data: bytes) -> str:
    return data.hex()


def _from_b64(value: str) -> bytes:
    return bytes.fromhex(value)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=64,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt, derived = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != "scrypt":
        return False
    computed = hashlib.scrypt(
        password.encode("utf-8"),
        salt=_from_b64(salt),
        n=int(n),
        r=int(r),
        p=int(p),
        dklen=64,
    )
    return hmac.compare_digest(computed, _from_b64(derived))


def _build_payload(*, subject: str, token_type: str, expires_delta: timedelta) -> dict[str, Any]:
    issued_at = datetime.now(UTC)
    expires_at = issued_at + expires_delta
    return {
        "sub": subject,
        "type": token_type,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(12),
    }


def create_access_token(subject: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    payload = _build_payload(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid access token type")
    return payload


def create_refresh_token() -> tuple[str, str, datetime]:
    settings = get_settings()
    plain = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return plain, token_hash, expires_at


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
