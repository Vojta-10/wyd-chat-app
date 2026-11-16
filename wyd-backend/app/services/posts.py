from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.post import get_feed
from app.schemas.post import PostPublic


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
            "is_liked": True,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


async def get_format_feed(
    session: AsyncSession, user: User, page_size: int, cursor: UUID | None
) -> dict[str, Any | list[PostPublic]]:
    result = await get_feed(session, user, cursor, page_size)
    has_more = len(result) >= page_size + 1
    next_cursor = None
    if has_more:
        next_cursor = result[page_size - 1].id
    formatted_results = [one_row_to_post(row) for row in result[:page_size]]
    return {"next_cursor": next_cursor, "posts": formatted_results}
