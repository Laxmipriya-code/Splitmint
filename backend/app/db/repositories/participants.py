from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import Group, Participant


class ParticipantRepository:
    def get_for_owner(
        self, db: Session, participant_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Participant | None:
        stmt = (
            select(Participant)
            .join(Participant.group)
            .where(Participant.id == participant_id, Group.owner_id == owner_id)
            .options(joinedload(Participant.group))
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_group_and_name_key(
        self,
        db: Session,
        *,
        group_id: uuid.UUID,
        name_key: str,
    ) -> Participant | None:
        stmt = select(Participant).where(
            Participant.group_id == group_id, Participant.name_key == name_key
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_group_participant(
        self, db: Session, *, group_id: uuid.UUID, participant_id: uuid.UUID
    ) -> Participant | None:
        stmt = select(Participant).where(
            Participant.group_id == group_id, Participant.id == participant_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def create(self, db: Session, participant: Participant) -> Participant:
        db.add(participant)
        db.flush()
        return participant

    def delete(self, db: Session, participant: Participant) -> None:
        db.delete(participant)
