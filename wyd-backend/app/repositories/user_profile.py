from typing import Any
from uuid import UUID

from asyncpg import UniqueViolationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DisallowedUpdateField, UserProfileInsertError
from app.models.user_profile import UserProfile

USER_PROFILE_UPDATEABLE_COLUMN_SET: frozenset[str] = frozenset(
    ["display_name", "bio", "pronouns", "theme", "accent_color"]
)


# TODO(test): a key outside the allowlist (e.g. "user_id") raises
#   DisallowedUpdateField and nothing is written to the DB
async def patch_user_profile(
    session: AsyncSession, user_profile: UserProfile, payload: dict[str, Any]
) -> UserProfile:
    for key, value in payload.items():
        if key not in USER_PROFILE_UPDATEABLE_COLUMN_SET:
            raise DisallowedUpdateField(key)
        setattr(user_profile, key, value)
    await session.flush()
    return user_profile


async def get_users_profile_by_user_id(
    session: AsyncSession, user_id: UUID
) -> UserProfile | None:
    result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )

    return result.scalar_one_or_none()


# TODO(test): build the test DB with Alembic migrations, not metadata.create_all():
#   create_all() doesn't create the users AFTER INSERT trigger, so every user
#   would be profile-less and tests would exercise a different path than prod.
# TODO(test): no profile row → one is inserted with display_name = username and
#   server defaults (bio '', pronouns '', theme 'system') loaded on the result
# TODO(test): race: the row already exists when we insert → UniqueViolationError
#   is swallowed, the existing row is returned, and the outer transaction is
#   still usable afterwards (the savepoint rolled back, not the whole request)
# TODO(test): user deleted before the insert → FK violation is re-raised
#   unchanged (not swallowed), request fails with a 500
async def insert_profile_if_missing(
    session: AsyncSession, user_id: UUID, username: str
) -> UserProfile:
    new_user_profile = UserProfile(display_name=username, user_id=user_id)
    try:
        async with session.begin_nested():
            session.add(new_user_profile)
            await session.flush()
    except IntegrityError as e:
        if not isinstance(e.driver_exception, UniqueViolationError):
            raise
    result = await get_users_profile_by_user_id(session, user_id)
    if result is None:
        raise UserProfileInsertError()
    return result
