import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.ai import MintSenseGroupSummaryRequest, MintSenseParseRequest
from app.services.ai import mintsense_service
from app.services.events import product_event_service

router = APIRouter()


@router.post("/parse-expense")
def parse_expense(
    payload: MintSenseParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    result = mintsense_service.parse_expense(db, current_user, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="ai.parse_expense",
        actor_user_id=current_user.id,
        group_id=payload.group_id,
        counters={
            "resolved_participant_count": len(result.resolved_participants),
            "validation_issue_count": len(result.validation_issues),
            "needs_confirmation": result.draft.needs_confirmation,
        },
    )
    return success_response(result.model_dump(mode="json"))


@router.post("/groups/{group_id}/summary")
def summarize_group(
    group_id: uuid.UUID,
    payload: MintSenseGroupSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    summary = mintsense_service.summarize_group(db, current_user, group_id, payload)
    product_event_service.safe_track_and_commit(
        db,
        event_name="ai.group_summary",
        actor_user_id=current_user.id,
        group_id=group_id,
        counters={"highlight_count": len(summary.highlights)},
    )
    return success_response(summary.model_dump(mode="json"))
