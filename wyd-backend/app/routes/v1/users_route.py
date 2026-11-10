from typing import Annotated

from fastapi import APIRouter, status

from app.dependencies import GetCurrentUserDep, SessionDep
from app.schemas.user import UserPatch, UserPublic, UserSelf, username_constraint
from app.services.users import get_public_profile, update_user_fields

users_router = APIRouter(tags=["users"])


# TODO(test): GET /me
#   - not logged in -> 401
#   - response never contains hashed_password
@users_router.get("/me", response_model=UserSelf)
async def get_me(current_user: GetCurrentUserDep):
    return current_user


# TODO(test): GET /{username}
#   - happy path: body is exactly {id, username, created_at} (no email, is_active)
#   - case-insensitive: GET /users/BOB finds "bob"
#   - unknown username -> 404
#   - inactive user -> 404 with a body identical to the unknown case
#   - GET /users/me still hits the /me route, not this one
@users_router.get(
    "/{username}", status_code=status.HTTP_200_OK, response_model=UserPublic
)
async def get_user_by_username(
    session: SessionDep, username: Annotated[str, username_constraint]
):
    return await get_public_profile(session, username)


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
