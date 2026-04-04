import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.expense import ExpenseUpsertRequest
from app.services.events import product_event_service
from app.services.expenses import expense_service

router = APIRouter()


@router.post("", status_code=201)
def create_expense(
    payload: ExpenseUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    expense = expense_service.create_expense(db, current_user, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="expense.create",
        actor_user_id=current_user.id,
        group_id=expense.group_id,
        expense_id=expense.id,
    )
    return success_response(expense.model_dump(mode="json"))


@router.get("")
def list_expenses(
    group_id: uuid.UUID,
    search: str | None = Query(default=None, min_length=1, max_length=200),
    participant_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    expenses = expense_service.list_expenses(
        db,
        current_user,
        group_id=group_id,
        search=search,
        participant_id=participant_id,
        date_from=date_from,
        date_to=date_to,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        size=size,
    )
    product_event_service.safe_track_and_commit(
        db,
        event_name="expense.list",
        actor_user_id=current_user.id,
        group_id=group_id,
        counters={
            "result_count": len(expenses.items),
            "page": page,
            "size": size,
        },
    )
    return success_response(expenses.model_dump(mode="json"))


@router.get("/{expense_id}")
def get_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    expense = expense_service.get_expense(db, current_user, expense_id)
    product_event_service.safe_track_and_commit(
        db,
        event_name="expense.get",
        actor_user_id=current_user.id,
        group_id=expense.group_id,
        expense_id=expense.id,
    )
    return success_response(expense.model_dump(mode="json"))


@router.put("/{expense_id}")
def update_expense(
    expense_id: uuid.UUID,
    payload: ExpenseUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    expense = expense_service.update_expense(db, current_user, expense_id, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="expense.update",
        actor_user_id=current_user.id,
        group_id=expense.group_id,
        expense_id=expense.id,
    )
    return success_response(expense.model_dump(mode="json"))


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    expense_service.delete_expense(db, current_user, expense_id)
    product_event_service.safe_track_and_commit(
        db,
        event_name="expense.delete",
        actor_user_id=current_user.id,
        expense_id=expense_id,
    )
