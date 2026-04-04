from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import ProductEvent
from app.db.repositories.product_events import ProductEventRepository

logger = logging.getLogger(__name__)


def _sanitize_counters(counters: dict[str, object] | None) -> dict[str, int | float | bool]:
    if not counters:
        return {}
    sanitized: dict[str, int | float | bool] = {}
    for key, value in counters.items():
        if not key or len(key) > 64:
            continue
        if isinstance(value, bool):
            sanitized[key] = value
        elif isinstance(value, int):
            sanitized[key] = value
        elif isinstance(value, float):
            sanitized[key] = value
    return sanitized


@dataclass(slots=True)
class ProductEventService:
    repository: ProductEventRepository

    def track(
        self,
        db: Session,
        *,
        event_name: str,
        actor_user_id: uuid.UUID | None = None,
        group_id: uuid.UUID | None = None,
        participant_id: uuid.UUID | None = None,
        expense_id: uuid.UUID | None = None,
        counters: dict[str, object] | None = None,
    ) -> None:
        event = ProductEvent(
            event_name=event_name,
            actor_user_id=actor_user_id,
            group_id=group_id,
            participant_id=participant_id,
            expense_id=expense_id,
            counters=_sanitize_counters(counters),
        )
        self.repository.create(db, event)

    def safe_track_and_commit(self, db: Session, **kwargs) -> None:
        try:
            self.track(db, **kwargs)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.warning("Failed to persist product event", exc_info=True)


product_event_service = ProductEventService(ProductEventRepository())
