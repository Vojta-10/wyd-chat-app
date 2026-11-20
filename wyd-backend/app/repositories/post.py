from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.exceptions import DisallowedUpdateField
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.user import User
from app.models.user_block import UserBlock
from app.models.user_profile import UserProfile

POST_UPDATEABLE_COLUMN_SET: frozenset[str] = frozenset(["description"])


def get_sql_stmt_post_info(user_id: UUID | None):
    exists_subq1 = (
        select(UserBlock.blocker_id)
        .where(Post.user_id == UserBlock.blocker_id, UserBlock.blocked_id == user_id)
        .exists()
    )
    exists_subq2 = (
        select(UserBlock.blocked_id)
        .where(Post.user_id == UserBlock.blocked_id, UserBlock.blocker_id == user_id)
        .exists()
    )
    stmt = (
        select(
            Post.id,
            Post.description,
            Post.like_count,
            Post.created_at,
            Post.updated_at,
            User.username,
            UserProfile.accent_color,
            func.coalesce(UserProfile.pronouns, "").label("pronouns"),
            UserProfile.pronouns,
            func.coalesce(UserProfile.display_name, User.username).label(
                "display_name"
            ),
            exists()
            .where(and_(PostLike.post_id == Post.id, PostLike.user_id == user_id))
            .label("is_liked"),
        )
        .join(Post.user)
        .outerjoin(User.user_profile)
        .where(User.is_active == True)
        .where(~exists_subq1, ~exists_subq2)
    )
    if user_id is None:
        stmt = stmt.where(UserProfile.visibility == "everybody")
    else:
        stmt = stmt.where(
            or_(UserProfile.visibility != "nobody", UserProfile.user_id == user_id)
        )
    return stmt


async def get_feed(
    session: AsyncSession,
    user_id: UUID | None,
    cursor: UUID | None,
    page_size: int = 20,
    target_user_id: UUID | None = None,
):
    stmt = get_sql_stmt_post_info(user_id)
    if target_user_id is not None:
        stmt = stmt.where(Post.user_id == target_user_id)
    if cursor is not None:
        stmt = stmt.where(Post.id < cursor)
    stmt = stmt.order_by(Post.id.desc()).limit(page_size + 1)
    result = await session.execute(stmt)
    result = result.all()
    return result


async def get_post_by_id(session: AsyncSession, post_id: UUID) -> Post | None:
    post = await session.get(Post, post_id)
    return post


async def get_post_by_id_full_user_info(
    session: AsyncSession, post_id: UUID, user_id: UUID | None = None
):
    stmt = get_sql_stmt_post_info(user_id).where(Post.id == post_id)
    result = await session.execute(stmt)
    return result.first()


async def create_post(session: AsyncSession, user_id: UUID, description: str) -> Post:
    new_post = Post(user_id=user_id, description=description)
    session.add(new_post)
    await session.flush()
    return new_post


async def delete_post(session: AsyncSession, post: Post) -> None:
    await session.delete(post)
    await session.flush()


async def patch_post(
    session: AsyncSession, post: Post, payload: dict[str, Any]
) -> Post | None:
    for key, value in payload.items():
        if key not in POST_UPDATEABLE_COLUMN_SET:
            raise DisallowedUpdateField(field=key)
        setattr(post, key, value)
    try:
        await session.flush()
    except StaleDataError:
        return None
    return post


async def like_post(session: AsyncSession, post_id: UUID, user_id: UUID):
    stmt = (
        insert(PostLike)
        .values(post_id=post_id, user_id=user_id)
        .on_conflict_do_nothing(index_elements=[PostLike.post_id, PostLike.user_id])
    )
    await session.execute(stmt)


async def unlike_post(session: AsyncSession, post_id: UUID, user_id: UUID):
    stmt = delete(PostLike).where(
        PostLike.user_id == user_id, PostLike.post_id == post_id
    )
    await session.execute(stmt)
