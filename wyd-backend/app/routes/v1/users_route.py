from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import GetCurrentUserDep, GetCurrentUserOptionalDep, SessionDep
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.post import PostPaginationOutput
from app.schemas.user import (
    UserPatch,
    UserPublic,
    UserSelf,
    username_constraint,
)
from app.schemas.user_profile import UserProfilePatch, UserProfileSelfBase
from app.services.posts import get_format_feed
from app.services.user_profiles import update_user_profile
from app.services.users import (
    block_user_service,
    delete_block_service,
    get_public_profile,
    update_user_fields,
)

users_router = APIRouter(tags=["users"])


# TODO(test): GET /me
#   - not logged in -> 401
#   - response never contains hashed_password
#   - nested user_profile includes theme
#   - profile row missing -> 200 with user_profile: null, and NO row is created
#     (GET never self-heals)
@users_router.get("/me", response_model=UserSelf)
async def get_me(current_user: GetCurrentUserDep) -> User:
    return current_user


# TODO(test): GET /{username}
#   - happy path: body is exactly {id, username, created_at, user_profile}
#     (no email, is_active); user_profile has no theme
#   - profile row missing -> 200 with user_profile: null, and NO row is created
#   - case-insensitive: GET /users/BOB finds "bob"
#   - unknown username -> 404
#   - inactive user -> 404 with a body identical to the unknown case
#   - GET /users/me still hits the /me route, not this one
#   - validation: 4 or 65 chars, or a space -> 422 before any DB query
#   - M2: blocked users (either direction) -> 404
@users_router.get(
    "/{username}", status_code=status.HTTP_200_OK, response_model=UserPublic
)
async def get_user_by_username(
    session: SessionDep,
    username: Annotated[str, username_constraint],
    user: GetCurrentUserOptionalDep,
) -> User:
    return await get_public_profile(session, username, user)


# TODO(test): PATCH /me
#   - not logged in -> 401
#   - authz: only the token's user changes; other users' rows are untouched
#   - mass assignment: email / is_active / id / hashed_password in body -> 422
#   - {"username": null} -> 422; {} -> 200 and nothing changes
#   - username taken by another user, different case -> 409 (not 500)
#   - own username with different case (Bobby -> bobby) -> 200
#   - updated_at moves forward after a real change
@users_router.patch("/me", status_code=status.HTTP_200_OK, response_model=UserSelf)
async def update_me(
    session: SessionDep, user: GetCurrentUserDep, payload: UserPatch
) -> User:
    excluded_payload = payload.model_dump(exclude_unset=True)
    return await update_user_fields(session, user, excluded_payload)


# TODO(test): happy path: PATCH {"bio": "hi"} → 200, only bio changed, response
#   has no user_id; works when accent_color is NULL (fresh profile)
# TODO(test): not logged in / invalid cookie → 401, nothing written
# TODO(test): extra field (e.g. "username" or "user_id") → 422 (extra="forbid")
# TODO(test): display_name null → 422; bio/pronouns null → ''; theme null → 'system'
@users_router.patch(
    "/me/profile", status_code=status.HTTP_200_OK, response_model=UserProfileSelfBase
)
async def update_me_profile(
    session: SessionDep, user: GetCurrentUserDep, payload: UserProfilePatch
) -> UserProfile:
    excluded_payload = payload.model_dump(exclude_unset=True)
    return await update_user_profile(session, user, excluded_payload)


# TODO(test): GET /{username}/posts
#   - unknown username -> 404; inactive user -> 404 (same body: no existence leak)
#   - user with 0 posts -> 200, posts [], next_cursor null
#   - different case ("Vojta_Test" vs "vojta_test") -> same result
#   - only this user's posts, newest first; paging with page_size=2 has no gaps
#     or duplicates and ends with next_cursor null
#   - logged out -> every is_liked false; logged in -> is_liked matches own likes
#   - malformed username ("ab", "a b") -> 422
@users_router.get(
    "/{username}/posts",
    status_code=status.HTTP_200_OK,
    response_model=PostPaginationOutput,
)
async def get_users_posts(
    session: SessionDep,
    username: Annotated[str, username_constraint],
    user: GetCurrentUserOptionalDep,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> PostPaginationOutput:
    return await get_format_feed(session, user, page_size, cursor, username)


@users_router.put("/{username}/block", status_code=status.HTTP_204_NO_CONTENT)
async def block_user(
    session: SessionDep,
    user: GetCurrentUserDep,
    username: Annotated[str, username_constraint],
) -> None:
    await block_user_service(session, user, username)


@users_router.delete("/{username}/block", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    session: SessionDep,
    user: GetCurrentUserDep,
    username: Annotated[str, username_constraint],
) -> None:
    await delete_block_service(session, user, username)
