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
)


async def update_user_fields(
    session: AsyncSession, user: User, payload: dict[str, Any]
) -> User:
    if not payload:
        return user
    await update_user(session, user, payload)
    return user


async def get_public_profile(session: AsyncSession, username: str) -> User:
    user = await get_user_by_username(session, username)
    if user is None or not user.is_active:
        raise UserNotFound()
    # TODO(M2): if the viewer and this user have blocked each other (either
    #   direction), raise the same UserNotFound. Also respect the profile's
    #   privacy setting once it exists.
    return user


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
