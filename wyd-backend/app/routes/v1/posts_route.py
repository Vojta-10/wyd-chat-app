from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import GetCurrentUserOptionalDep, SessionDep
from app.schemas.post import PostPaginationOutput
from app.services.posts import get_format_feed

posts_router = APIRouter(tags=["posts"])


# TODO(test): GET /v1/posts/ (feed)
#   - logged out -> 200, every is_liked is false
#   - logged in -> is_liked true only for posts *this* user liked (not another user's likes)
#   - posts by inactive authors are not in the feed
#   - paging: page_size=N returns N items, next_cursor continues without gaps
#     or duplicates, last page has has_more false
#   - page_size 0 or 101 -> 422; malformed cursor -> 422
@posts_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=PostPaginationOutput,
)
async def get_feed_posts(
    session: SessionDep,
    user: GetCurrentUserOptionalDep,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
):
    return await get_format_feed(session, user, page_size, cursor)
