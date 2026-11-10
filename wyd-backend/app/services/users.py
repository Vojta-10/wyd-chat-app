from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFound
from app.models.user import User
from app.repositories.user import get_user_by_username, update_user


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
