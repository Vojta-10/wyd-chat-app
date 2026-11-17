from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.post_like import PostLike
from app.models.user import User
from app.models.user_profile import UserProfile


async def get_feed(
    session: AsyncSession,
    user_id: UUID | None,
    cursor: UUID | None,
    page_size: int = 20,
):
    stmt = (
        select(
            Post.id,
            Post.description,
            Post.like_count,
            Post.created_at,
            Post.updated_at,
            User.username,
            UserProfile.accent_color,
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
    )

    if cursor is not None:
        stmt = stmt.where(Post.id < cursor)
    stmt = stmt.order_by(Post.id.desc()).limit(page_size + 1)
    result = await session.execute(stmt)
    result = result.all()
    return result
