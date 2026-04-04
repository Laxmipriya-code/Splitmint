from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.db.models import Participant, User
from app.db.repositories.expenses import ExpenseRepository
from app.db.repositories.participants import ParticipantRepository
from app.schemas.participant import (
    ParticipantCreateRequest,
    ParticipantRead,
    ParticipantUpdateRequest,
)
from app.services.groups import GroupService, default_participant_color, group_service
from app.utils.money import normalize_name_key


@dataclass(slots=True)
class ParticipantService:
    participant_repository: ParticipantRepository
    expense_repository: ExpenseRepository
    group_service: GroupService

    def add_participant(
        self,
        db: Session,
        owner: User,
        group_id: uuid.UUID,
        payload: ParticipantCreateRequest,
    ) -> ParticipantRead:
        group = self.group_service.get_owned_group_or_404(db, owner, group_id)
        self.group_service.ensure_capacity_for_new_participant(db, group)

        name_key = normalize_name_key(payload.name)
        existing = self.participant_repository.get_by_group_and_name_key(
            db, group_id=group_id, name_key=name_key
        )
        if existing is not None:
            raise BadRequestError("Participant name already exists in this group")

        participant = Participant(
            group_id=group.id,
            name=payload.name,
            name_key=name_key,
            avatar_url=str(payload.avatar_url) if payload.avatar_url else None,
            color_hex=payload.color_hex or default_participant_color(payload.name),
        )
        self.participant_repository.create(db, participant)
        db.commit()
        db.refresh(participant)
        return ParticipantRead.model_validate(participant)

    def update_participant(
        self,
        db: Session,
        owner: User,
        participant_id: uuid.UUID,
        payload: ParticipantUpdateRequest,
    ) -> ParticipantRead:
        participant = self.participant_repository.get_for_owner(db, participant_id, owner.id)
        if participant is None:
            raise NotFoundError("Participant not found", code="participant_not_found")

        if payload.name and normalize_name_key(payload.name) != participant.name_key:
            existing = self.participant_repository.get_by_group_and_name_key(
                db,
                group_id=participant.group_id,
                name_key=normalize_name_key(payload.name),
            )
            if existing is not None and existing.id != participant.id:
                raise BadRequestError("Participant name already exists in this group")
            participant.name = payload.name
            participant.name_key = normalize_name_key(payload.name)

        if payload.avatar_url is not None:
            participant.avatar_url = str(payload.avatar_url)
        if payload.color_hex is not None:
            participant.color_hex = payload.color_hex

        db.commit()
        db.refresh(participant)
        return ParticipantRead.model_validate(participant)

    def remove_participant(self, db: Session, owner: User, participant_id: uuid.UUID) -> None:
        participant = self.participant_repository.get_for_owner(db, participant_id, owner.id)
        if participant is None:
            raise NotFoundError("Participant not found", code="participant_not_found")
        if participant.is_owner:
            raise BadRequestError("The group owner cannot be removed")

        if self.expense_repository.participant_has_history(db, participant.id):
            participant.is_active = False
        else:
            self.participant_repository.delete(db, participant)
        db.commit()


participant_service = ParticipantService(
    ParticipantRepository(), ExpenseRepository(), group_service
)
