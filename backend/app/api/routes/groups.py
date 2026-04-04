import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.group import GroupCreateRequest, GroupUpdateRequest
from app.schemas.participant import ParticipantCreateRequest
from app.services.events import product_event_service
from app.services.groups import group_service
from app.services.participants import participant_service

router = APIRouter()


@router.post("", status_code=201)
def create_group(
    payload: GroupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    group = group_service.create_group(db, current_user, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="group.create",
        actor_user_id=current_user.id,
        group_id=group.id,
    )
    return success_response(group.model_dump(mode="json"))


@router.get("")
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    groups = group_service.list_groups(db, current_user)
    return success_response([group.model_dump(mode="json") for group in groups])


@router.get("/{group_id}")
def get_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    group = group_service.get_group(db, current_user, group_id)
    return success_response(group.model_dump(mode="json"))


@router.put("/{group_id}")
def update_group(
    group_id: uuid.UUID,
    payload: GroupUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    group = group_service.update_group(db, current_user, group_id, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="group.update",
        actor_user_id=current_user.id,
        group_id=group.id,
    )
    return success_response(group.model_dump(mode="json"))


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    group_service.delete_group(db, current_user, group_id)
    product_event_service.safe_track_and_commit(
        db,
        event_name="group.delete",
        actor_user_id=current_user.id,
        group_id=group_id,
    )


@router.post("/{group_id}/participants", status_code=201)
def add_group_participant(
    group_id: uuid.UUID,
    payload: ParticipantCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    participant = participant_service.add_participant(db, current_user, group_id, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="participant.create",
        actor_user_id=current_user.id,
        group_id=group_id,
        participant_id=participant.id,
    )
    return success_response(participant.model_dump(mode="json"))
