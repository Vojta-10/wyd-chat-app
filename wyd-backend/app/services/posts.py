from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PostForbiddenToAccess, PostNotFound, UserNotFound
from app.models.user import User
from app.repositories.post import (
    create_post,
    delete_post,
    get_feed,
    get_post_by_id,
    get_post_by_id_full_user_info,
    like_post,
    patch_post,
    unlike_post,
)
from app.repositories.user import get_user_by_username_no_profile_join
from app.schemas.post import PostCreate, PostPaginationOutput, PostPublic


def one_row_to_post(row) -> PostPublic:
    return PostPublic.model_validate(
        {
            "id": row.id,
            "author": {
                "display_name": row.display_name,
                "username": row.username,
                "accent_color": row.accent_color,
                "pronouns": row.pronouns,
            },
            "description": row.description,
            "like_count": row.like_count,
            "is_liked": row.is_liked,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


async def get_format_feed(
    session: AsyncSession,
    user: User | None,
    page_size: int,
    cursor: UUID | None,
    target_username: str | None = None,
) -> PostPaginationOutput:
    user_id = user.id if user is not None else None
    target_user = None
    if target_username is not None:
        target_user = await get_user_by_username_no_profile_join(
            session, target_username
        )
        if target_user is None or not target_user.is_active:
            raise UserNotFound()
    result = await get_feed(
        session,
        user_id,
        cursor,
        page_size,
        target_user.id if target_user is not None else None,
    )
    has_more = len(result) >= page_size + 1
    next_cursor = None
    if has_more:
        next_cursor = result[page_size - 1].id
    formatted_results = [one_row_to_post(row) for row in result[:page_size]]
    return PostPaginationOutput.model_validate(
        {"next_cursor": next_cursor, "posts": formatted_results}
    )


async def create_post_service(
    session: AsyncSession, user_id: UUID, payload: PostCreate
) -> PostPublic:
    post = await create_post(session, user_id, payload.description)
    post = await get_post_by_id_full_user_info(session, post.id, user_id)
    if post is None:
        raise PostNotFound()
    return one_row_to_post(post)


async def get_post_service(
    session: AsyncSession, post_id: UUID, user: User | None
) -> PostPublic:
    user_id = user.id if user is not None else None
    post = await get_post_by_id_full_user_info(session, post_id, user_id)
    if post is None:
        raise PostNotFound()
    return one_row_to_post(post)


async def delete_post_service(session: AsyncSession, post_id: UUID, user: User):
    post = await get_post_by_id(session, post_id)
    if post is None:
        raise PostNotFound()
    if post.user_id != user.id:
        raise PostForbiddenToAccess()
    await delete_post(session, post)


async def patch_post_service(
    session: AsyncSession, post_id: UUID, user: User, payload: dict[str, Any]
) -> PostPublic:
    post = await get_post_by_id(session, post_id)
    if post is None:
        raise PostNotFound()
    if post.user_id != user.id:
        raise PostForbiddenToAccess()
    updated_post = await patch_post(session, post, payload)
    if updated_post is None:
        raise PostNotFound()
    post = await get_post_by_id_full_user_info(session, post_id, user.id)
    if post is None:
        raise PostNotFound()
    return one_row_to_post(post)


async def like_post_service(
    session: AsyncSession, post_id: UUID, user: User
) -> PostPublic:
    post = await get_post_by_id_full_user_info(session, post_id)
    if post is None:
        raise PostNotFound()
    await like_post(session, post_id, user.id)
    post = await get_post_by_id_full_user_info(session, post_id, user_id=user.id)
    return one_row_to_post(post)


async def unlike_post_service(
    session: AsyncSession, post_id: UUID, user: User
) -> PostPublic:
    post = await get_post_by_id_full_user_info(session, post_id)
    if post is None:
        raise PostNotFound()
    await unlike_post(session, post_id, user.id)
    post = await get_post_by_id_full_user_info(session, post_id, user.id)
    return one_row_to_post(post)
