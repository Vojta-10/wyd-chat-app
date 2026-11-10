from typing import Any
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DisallowedUpdateField
from app.models.user import User
from app.utils.except_error import extract_db_error_index_constraint_and_raise_error

USER_UPDATEABLE_COLUMN_SET: frozenset[str] = frozenset(["username"])


async def create_user(
    session: AsyncSession,
    hashed_password: SecretStr,
    *,
    username: str,
    email: str,
) -> User:
    new_user = User(
        username=username,
        hashed_password=hashed_password.get_secret_value(),
        email=email,
    )
    session.add(new_user)
    try:
        await session.flush()
    except IntegrityError as e:
        extract_db_error_index_constraint_and_raise_error(e)
    return new_user


# TODO(test): a key outside the allowlist (e.g. "is_active") raises
#   DisallowedUpdateField and nothing is written to the DB
async def update_user(
    session: AsyncSession, user: User, payload: dict[str, Any]
) -> None:
    for key, value in payload.items():
        if key not in USER_UPDATEABLE_COLUMN_SET:
            raise DisallowedUpdateField(key)
        setattr(user, key, value)
    try:
        await session.flush()
    except IntegrityError as e:
        extract_db_error_index_constraint_and_raise_error(e)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(func.lower(User.email) == func.lower(email))
    )
    user = result.scalar_one_or_none()
    return user


async def update_user_hash(
    session: AsyncSession, user: User, new_hashed_password: str
) -> None:
    user.hashed_password = new_hashed_password
    await session.flush()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
