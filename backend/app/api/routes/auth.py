from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, UserRead
from app.services.auth import auth_service
from app.services.events import product_event_service

router = APIRouter()


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    session = auth_service.register(db, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="auth.register",
        actor_user_id=session.user.id,
    )
    return success_response(session.model_dump(mode="json"))


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    session = auth_service.login(db, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="auth.login",
        actor_user_id=session.user.id,
    )
    return success_response(session.model_dump(mode="json"))


@router.post("/refresh")
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    session = auth_service.refresh(db, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="auth.refresh",
        actor_user_id=session.user.id,
    )
    return success_response(session.model_dump(mode="json"))


@router.post("/logout")
def logout(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, object]:
    auth_service.logout(db, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="auth.logout",
        actor_user_id=_.id,
    )
    return success_response({"logged_out": True})


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    return success_response(UserRead.model_validate(current_user).model_dump(mode="json"))
