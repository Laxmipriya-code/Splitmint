from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import ProductEvent


class ProductEventRepository:
    def create(self, db: Session, event: ProductEvent) -> ProductEvent:
        db.add(event)
        db.flush()
        return event
