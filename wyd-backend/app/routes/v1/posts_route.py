from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import GetCurrentUserDep, SessionDep
from app.schemas.post import PostPaginationOutput
from app.services.posts import get_format_feed

posts_router = APIRouter(tags=["posts"])


@posts_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=PostPaginationOutput,
)
async def get_feed_posts(
    session: SessionDep,
    user: GetCurrentUserDep,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
):
    return await get_format_feed(session, user, page_size, cursor)
