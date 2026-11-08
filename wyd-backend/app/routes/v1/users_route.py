from fastapi import APIRouter, status

from app.dependencies import GetCurrentUserDep, SessionDep
from app.schemas.user import UserPatch, UserSelf
from app.services.users import update_user_fields

users_router = APIRouter(tags=["users"])


@users_router.get("/me", response_model=UserSelf)
async def get_me(current_user: GetCurrentUserDep):
    return current_user


@users_router.patch("/me", status_code=status.HTTP_200_OK, response_model=UserSelf)
async def update_me(session: SessionDep, user: GetCurrentUserDep, payload: UserPatch):
    excluded_payload = payload.model_dump(exclude_unset=True)
    return await update_user_fields(session, user, excluded_payload)
