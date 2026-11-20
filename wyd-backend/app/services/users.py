from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BlockSelfError, UserNotFound
from app.models.user import User
from app.repositories.user import (
    block_user,
    delete_likes_both_directions,
    get_user_by_username,
    get_user_by_username_no_profile_join,
    unblock_user,
    update_user,
    user_block_check_both_direction,
)


async def update_user_fields(
    session: AsyncSession, user: User, payload: dict[str, Any]
) -> User:
    if not payload:
        return user
    await update_user(session, user, payload)
    return user


async def get_public_profile(
    session: AsyncSession, username: str, user: User | None = None
) -> User:
    target_user = await get_user_by_username(session, username)
    if (
        target_user is None
        or not target_user.is_active
        or (
            user is not None
            and await user_block_check_both_direction(session, user, target_user.id)
        )
    ):
        raise UserNotFound()
    # TODO(M2): if the viewer and this user have blocked each other (either
    #   direction), raise the same UserNotFound. Also respect the profile's
    #   privacy setting once it exists.
    return target_user


# TODO(test): block / unblock (PUT and DELETE /v1/users/block/{username})
#   - not logged in -> 401
#   - happy path: A blocks B -> 204, one row (blocker=A, blocked=B)
#   - idempotent: A blocks B twice -> 204 both times, still one row
#   - self-block, different case (alice blocks ALICE) -> 400, never a 500
#   - unknown username -> 404
#   - blocked by target: A blocked B, then B blocks A -> 204 (no 404/409, the
#     block isn't revealed), and both rows exist
#   - likes: A's likes on B's posts and B's likes on A's posts are deleted,
#     like_count on those posts drops by the same amount
#   - likes: both A's and B's likes on a third user C's post survive
#   - unblock only removes the caller's own row: A blocked B, B blocked A,
#     A unblocks -> B's row still there, they still can't see each other
#   - unblock twice / unblock someone never blocked -> 204
async def block_user_service(
    session: AsyncSession, user: User, target_username: str
) -> None:
    if user.username.lower() == target_username.lower():
        raise BlockSelfError()
    target_user = await get_user_by_username_no_profile_join(session, target_username)
    if target_user is None:
        raise UserNotFound()
    await block_user(session, user.id, target_user.id)
    await delete_likes_both_directions(session, user.id, target_user.id)


async def delete_block_service(
    session: AsyncSession, user: User, target_username: str
) -> None:
    target_user = await get_user_by_username_no_profile_join(session, target_username)
    if target_user is None:
        raise UserNotFound()
    await unblock_user(session, user.id, target_user.id)
