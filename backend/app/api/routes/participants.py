import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.participant import ParticipantUpdateRequest
from app.services.events import product_event_service
from app.services.participants import participant_service

router = APIRouter()


@router.put("/{participant_id}")
def update_participant(
    participant_id: uuid.UUID,
    payload: ParticipantUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    participant = participant_service.update_participant(db, current_user, participant_id, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="participant.update",
        actor_user_id=current_user.id,
        group_id=participant.group_id,
        participant_id=participant.id,
    )
    return success_response(participant.model_dump(mode="json"))


@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    participant_service.remove_participant(db, current_user, participant_id)
    product_event_service.safe_track_and_commit(
        db,
        event_name="participant.delete",
        actor_user_id=current_user.id,
        participant_id=participant_id,
    )
