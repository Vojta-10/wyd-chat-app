from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_profile import UserProfile
from app.repositories.user_profile import (
    get_users_profile_by_user_id,
    insert_profile_if_missing,
    patch_user_profile,
)


async def get_user_profile_heal_if_missing(
    session: AsyncSession, user: User
) -> UserProfile:
    user_profile = await get_users_profile_by_user_id(session, user.id)
    if user_profile is None:
        # TODO(M6): log a warning here (user_id only, no username/email): the
        #   trigger's "every user has a profile" guarantee broke and we healed it.
        user_profile = await insert_profile_if_missing(session, user.id, user.username)
    return user_profile


async def update_user_profile(
    session: AsyncSession, user: User, payload: dict[str, Any]
) -> UserProfile:
    user_profile = await get_user_profile_heal_if_missing(session, user)
    updated_user_profile = await patch_user_profile(session, user_profile, payload)
    return updated_user_profile
