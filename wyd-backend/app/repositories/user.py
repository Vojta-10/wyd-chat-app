from typing import Any
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import and_, delete, or_

from app.core.exceptions import DisallowedUpdateField
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.user import User
from app.models.user_block import UserBlock
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
        select(User)
        .where(func.lower(User.email) == func.lower(email))
        .options(joinedload(User.user_profile))
    )
    user = result.scalar_one_or_none()
    return user


async def update_user_hash(
    session: AsyncSession, user: User, new_hashed_password: str
) -> None:
    user.hashed_password = new_hashed_password
    await session.flush()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id).options(joinedload(User.user_profile))
    )
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(
        select(User)
        .where(func.lower(User.username) == func.lower(username))
        .options(joinedload(User.user_profile))
    )
    return result.scalar_one_or_none()


async def get_user_by_username_no_profile_join(
    session: AsyncSession, username: str
) -> User | None:
    result = await session.execute(
        select(User).where(func.lower(User.username) == func.lower(username))
    )
    return result.scalar_one_or_none()


async def block_user(session: AsyncSession, blocker_id: UUID, blocked_id: UUID) -> None:
    insert_stmt = insert(UserBlock).values(blocker_id=blocker_id, blocked_id=blocked_id)
    await session.execute(
        insert_stmt.on_conflict_do_nothing(
            index_elements=[UserBlock.blocker_id, UserBlock.blocked_id]
        )
    )


async def unblock_user(
    session: AsyncSession, blocker_id: UUID, blocked_id: UUID
) -> None:
    await session.execute(
        delete(UserBlock).where(
            UserBlock.blocker_id == blocker_id, UserBlock.blocked_id == blocked_id
        )
    )


async def delete_likes_both_directions(
    session: AsyncSession, blocker_id: UUID, blocked_id: UUID
) -> None:
    await session.execute(
        delete(PostLike).where(
            or_(
                and_(
                    PostLike.user_id == blocker_id,
                    PostLike.post_id.in_(
                        select(Post.id).where(Post.user_id == blocked_id)
                    ),
                ),
                and_(
                    PostLike.user_id == blocked_id,
                    PostLike.post_id.in_(
                        select(Post.id).where(Post.user_id == blocker_id)
                    ),
                ),
            )
        )
    )
