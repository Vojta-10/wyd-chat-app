from fastapi import APIRouter

users_router = APIRouter(tags=["users"])
from app.dependencies import GetCurrentUserDep
from app.schemas.user import UserSelf


@users_router.get("/me", response_model=UserSelf)
async def get_me(current_user: GetCurrentUserDep):
    return current_user
