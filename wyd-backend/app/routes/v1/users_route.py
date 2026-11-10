from fastapi import APIRouter, status

from app.dependencies import GetCurrentUserDep, SessionDep
from app.schemas.user import UserPatch, UserSelf
from app.services.users import update_user_fields

users_router = APIRouter(tags=["users"])


# TODO(test): GET /me
#   - not logged in -> 401
#   - response never contains hashed_password
@users_router.get("/me", response_model=UserSelf)
async def get_me(current_user: GetCurrentUserDep):
    return current_user


# TODO(test): PATCH /me
#   - not logged in -> 401
#   - authz: only the token's user changes; other users' rows are untouched
#   - mass assignment: email / is_active / id / hashed_password in body -> 422
#   - {"username": null} -> 422; {} -> 200 and nothing changes
#   - username taken by another user, different case -> 409 (not 500)
#   - own username with different case (Bobby -> bobby) -> 200
#   - updated_at moves forward after a real change
@users_router.patch("/me", status_code=status.HTTP_200_OK, response_model=UserSelf)
async def update_me(session: SessionDep, user: GetCurrentUserDep, payload: UserPatch):
    excluded_payload = payload.model_dump(exclude_unset=True)
    return await update_user_fields(session, user, excluded_payload)
