from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.db.models import Group, Participant, User
from app.db.repositories.groups import GroupRepository
from app.schemas.balance import BalanceSnapshotRead
from app.schemas.group import GroupCreateRequest, GroupListItemRead, GroupRead, GroupUpdateRequest
from app.services.balances import BalanceService, balance_service
from app.utils.money import normalize_name_key

DEFAULT_COLORS = ["#1D4ED8", "#0F766E", "#B45309", "#7C3AED", "#BE123C", "#0369A1"]


def default_participant_color(seed: str) -> str:
    return DEFAULT_COLORS[sum(ord(char) for char in seed) % len(DEFAULT_COLORS)]


@dataclass(slots=True)
class GroupService:
    group_repository: GroupRepository
    balance_service: BalanceService

    def create_group(self, db: Session, owner: User, payload: GroupCreateRequest) -> GroupRead:
        group = Group(name=payload.name, owner_id=owner.id)
        owner_name = owner.display_name or owner.email.split("@", 1)[0]
        group.participants.append(
            Participant(
                name=owner_name,
                name_key=normalize_name_key(owner_name),
                user_id=owner.id,
                is_owner=True,
                color_hex=default_participant_color(owner.email),
            )
        )
        self.group_repository.create(db, group)
        db.commit()
        db.refresh(group)
        reloaded = self.group_repository.get_for_owner(db, group.id, owner.id)
        return self._to_group_read(reloaded)

    def list_groups(self, db: Session, owner: User) -> list[GroupListItemRead]:
        groups = self.group_repository.list_for_owner(db, owner.id)
        results: list[GroupListItemRead] = []
        for group in groups:
            summary = self.balance_service.build_snapshot(group)
            active_count = len(
                [participant for participant in group.participants if participant.is_active]
            )
            results.append(
                GroupListItemRead(
                    id=group.id,
                    name=group.name,
                    active_participant_count=active_count,
                    total_spent=summary.total_spent,
                    you_owe=summary.you_owe,
                    you_are_owed=summary.you_are_owed,
                    created_at=group.created_at,
                    updated_at=group.updated_at,
                    version=group.version,
                )
            )
        return results

    def get_group(self, db: Session, owner: User, group_id: uuid.UUID) -> GroupRead:
        group = self.group_repository.get_for_owner(db, group_id, owner.id)
        if group is None:
            raise NotFoundError("Group not found", code="group_not_found")
        return self._to_group_read(group)

    def get_balance_snapshot(
        self, db: Session, owner: User, group_id: uuid.UUID
    ) -> BalanceSnapshotRead:
        group = self.group_repository.get_for_owner(db, group_id, owner.id)
        if group is None:
            raise NotFoundError("Group not found", code="group_not_found")
        return self.balance_service.build_snapshot(group)

    def update_group(
        self, db: Session, owner: User, group_id: uuid.UUID, payload: GroupUpdateRequest
    ) -> GroupRead:
        group = self.group_repository.get_for_owner(db, group_id, owner.id)
        if group is None:
            raise NotFoundError("Group not found", code="group_not_found")
        group.name = payload.name
        db.commit()
        db.refresh(group)
        reloaded = self.group_repository.get_for_owner(db, group_id, owner.id)
        return self._to_group_read(reloaded)

    def delete_group(self, db: Session, owner: User, group_id: uuid.UUID) -> None:
        group = self.group_repository.get_for_owner_basic(db, group_id, owner.id)
        if group is None:
            raise NotFoundError("Group not found", code="group_not_found")
        self.group_repository.delete(db, group)
        db.commit()

    def get_owned_group_or_404(self, db: Session, owner: User, group_id: uuid.UUID) -> Group:
        group = self.group_repository.get_for_owner_basic(db, group_id, owner.id)
        if group is None:
            raise NotFoundError("Group not found", code="group_not_found")
        return group

    def ensure_capacity_for_new_participant(self, db: Session, group: Group) -> None:
        active_count = self.group_repository.active_participant_count(db, group.id)
        if active_count >= 4:
            raise BadRequestError("Groups can contain at most 4 active participants")

    def _to_group_read(self, group: Group) -> GroupRead:
        owner_participant = next(
            participant for participant in group.participants if participant.is_owner
        )
        summary = self.balance_service.build_snapshot(group)
        participants = sorted(
            group.participants,
            key=lambda item: (not item.is_active, not item.is_owner, item.name.lower()),
        )
        return GroupRead(
            id=group.id,
            name=group.name,
            owner_participant_id=owner_participant.id,
            participants=participants,
            summary=summary,
            created_at=group.created_at,
            updated_at=group.updated_at,
            version=group.version,
        )


group_service = GroupService(GroupRepository(), balance_service)
