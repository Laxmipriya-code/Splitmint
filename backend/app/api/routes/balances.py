import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.services.events import product_event_service
from app.services.groups import group_service

router = APIRouter()


@router.get("/{group_id}/balances")
def get_balances(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    snapshot = group_service.get_balance_snapshot(db, current_user, group_id)
    product_event_service.safe_track_and_commit(
        db,
        event_name="balance.snapshot",
        actor_user_id=current_user.id,
        group_id=group_id,
        counters={
            "participant_count": len(snapshot.balances),
            "settlement_count": len(snapshot.settlements),
        },
    )
    return success_response(snapshot.model_dump(mode="json"))


@router.get("/{group_id}/settlements")
def get_settlements(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    snapshot = group_service.get_balance_snapshot(db, current_user, group_id)
    product_event_service.safe_track_and_commit(
        db,
        event_name="balance.settlements",
        actor_user_id=current_user.id,
        group_id=group_id,
        counters={"settlement_count": len(snapshot.settlements)},
    )
    return success_response(
        {"settlements": [item.model_dump(mode="json") for item in snapshot.settlements]}
    )
