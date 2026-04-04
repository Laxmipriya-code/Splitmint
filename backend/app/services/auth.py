from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import BadRequestError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.models import RefreshToken, User
from app.db.repositories.refresh_tokens import RefreshTokenRepository
from app.db.repositories.users import UserRepository
from app.schemas.auth import (
    AuthSession,
    AuthTokens,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    UserRead,
)


def default_display_name(email: str) -> str:
    return email.split("@", 1)[0]


@dataclass(slots=True)
class AuthService:
    user_repository: UserRepository
    refresh_token_repository: RefreshTokenRepository

    def register(self, db: Session, payload: RegisterRequest) -> AuthSession:
        if self.user_repository.get_by_email(db, payload.email):
            raise BadRequestError("Email is already registered", details={"email": payload.email})

        user = User(
            email=payload.email,
            display_name=payload.display_name or default_display_name(payload.email),
            password_hash=hash_password(payload.password.get_secret_value()),
        )
        self.user_repository.create(db, user)
        session = self._issue_session(db, user)
        db.commit()
        db.refresh(user)
        return session

    def login(self, db: Session, payload: LoginRequest) -> AuthSession:
        user = self.user_repository.get_by_email(db, payload.email)
        if user is None or not verify_password(
            payload.password.get_secret_value(), user.password_hash
        ):
            raise UnauthorizedError("Invalid email or password")
        session = self._issue_session(db, user)
        db.commit()
        db.refresh(user)
        return session

    def refresh(self, db: Session, payload: RefreshTokenRequest) -> AuthSession:
        token_hash = hash_refresh_token(payload.refresh_token)
        stored = self.refresh_token_repository.get_active(db, token_hash)
        if stored is None:
            raise UnauthorizedError("Invalid or expired refresh token")

        self.refresh_token_repository.revoke(db, stored)
        session = self._issue_session(db, stored.user)
        db.commit()
        db.refresh(stored.user)
        return session

    def logout(self, db: Session, payload: RefreshTokenRequest) -> None:
        token_hash = hash_refresh_token(payload.refresh_token)
        stored = self.refresh_token_repository.get_active(db, token_hash)
        if stored is None:
            return
        self.refresh_token_repository.revoke(db, stored)
        db.commit()

    def _issue_session(self, db: Session, user: User) -> AuthSession:
        plain_refresh_token, refresh_token_hash, refresh_expiry = create_refresh_token()
        self.refresh_token_repository.create(
            db,
            RefreshToken(user_id=user.id, token_hash=refresh_token_hash, expires_at=refresh_expiry),
        )
        settings = get_settings()
        tokens = AuthTokens(
            access_token=create_access_token(str(user.id), settings),
            refresh_token=plain_refresh_token,
            expires_in_seconds=settings.access_token_expire_minutes * 60,
        )
        return AuthSession(user=UserRead.model_validate(user), tokens=tokens)


auth_service = AuthService(UserRepository(), RefreshTokenRepository())
