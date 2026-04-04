from fastapi import APIRouter

from app.api.routes import ai, auth, balances, expenses, groups, participants

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(participants.router, prefix="/participants", tags=["participants"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
api_router.include_router(balances.router, prefix="/groups", tags=["balances"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
