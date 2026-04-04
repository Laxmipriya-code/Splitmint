from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RefreshToken


class RefreshTokenRepository:
    def create(self, db: Session, token: RefreshToken) -> RefreshToken:
        db.add(token)
        db.flush()
        return token

    def get_active(self, db: Session, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        return db.execute(stmt).scalar_one_or_none()

    def revoke(self, db: Session, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        db.flush()
