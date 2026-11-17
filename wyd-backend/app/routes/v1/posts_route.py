from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import GetCurrentUserDep, GetCurrentUserOptionalDep, SessionDep
from app.schemas.post import (
    PostCreate,
    PostPaginationOutput,
    PostPatch,
    PostPublic,
)
from app.services.posts import (
    create_post_service,
    delete_post_service,
    get_format_feed,
    get_post_service,
    like_post_service,
    patch_post_service,
    unlike_post_service,
)

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


# TODO(test): GET /v1/posts/{post_id}
#   - logged out -> 200, is_liked false; logged in as the liker -> is_liked true
#   - unknown id -> 404; malformed id -> 422
#   - post by an inactive author -> 404 (same as the feed)
#   - author without a user_profiles row -> 200, display_name = username, pronouns ""
#   - response has exactly the same shape as a feed item
@posts_router.get(
    "/{post_id}", status_code=status.HTTP_200_OK, response_model=PostPublic
)
async def get_post(session: SessionDep, post_id: UUID, user: GetCurrentUserOptionalDep):
    return await get_post_service(session, post_id, user)


# TODO(test): POST create
#   - not logged in -> 401
#   - 201, author = the logged-in user, like_count 0, is_liked false
#   - body with "user_id" (or any extra field) -> 422 (cannot post as someone else)
#   - description missing / "" / only spaces / 257 chars / control chars -> 422
#   - "\r\n" is stored as "\n"
@posts_router.post("/", status_code=status.HTTP_201_CREATED, response_model=PostPublic)
async def create_new_post(
    session: SessionDep, user: GetCurrentUserDep, payload: PostCreate
):
    return await create_post_service(session, user.id, payload)


# TODO(test): DELETE /v1/posts/{post_id} (security regression: IDOR)
#   - not logged in -> 401
#   - user B deletes user A's post -> 403 and the post still exists
#   - owner deletes -> 204 with an empty body, then GET -> 404
#   - unknown id -> 404; deleting twice -> second call 404
#   - the post's post_likes rows are gone too (FK cascade)
@posts_router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(session: SessionDep, post_id: UUID, user: GetCurrentUserDep):
    return await delete_post_service(session, post_id, user)


# TODO(test): PATCH /v1/posts/{post_id} (security regression: IDOR, mass assignment)
#   - not logged in -> 401
#   - user B patches user A's post -> 403 and the description is unchanged
#   - body with "user_id" / "like_count" / "id" -> 422 (extra="forbid")
#   - {"description": null} -> 422; {} -> 200 and nothing changes
#   - owner patches -> updated_at moves, like_count and created_at unchanged
#   - unknown id -> 404
#   - race: post deleted between the ownership check and the flush -> 404, not 500
@posts_router.patch(
    "/{post_id}", status_code=status.HTTP_200_OK, response_model=PostPublic
)
async def patch_post(
    session: SessionDep, user: GetCurrentUserDep, post_id: UUID, payload: PostPatch
):
    excluded_payload = payload.model_dump(exclude_unset=True)
    return await patch_post_service(session, post_id, user, excluded_payload)


# TODO(test): like (PUT)
#   - not logged in -> 401
#   - like -> 200, is_liked true, like_count +1 (check the DB too)
#   - like twice -> second call 200, like_count unchanged, still one post_likes row
#   - unknown post -> 404; post by an inactive author -> 404
#   - user A's like doesn't make is_liked true for user B
@posts_router.put(
    "/{post_id}/like", status_code=status.HTTP_200_OK, response_model=PostPublic
)
async def like_post(session: SessionDep, user: GetCurrentUserDep, post_id: UUID):
    return await like_post_service(session, post_id, user)


# TODO(test): unlike (DELETE)
#   - not logged in -> 401
#   - unlike -> 200, is_liked false, like_count -1
#   - unlike a post you never liked -> 200, like_count unchanged (never below 0)
#   - user B's unlike never removes user A's like
#   - unknown post -> 404
@posts_router.delete(
    "/{post_id}/like", status_code=status.HTTP_200_OK, response_model=PostPublic
)
async def unlike_post(session: SessionDep, user: GetCurrentUserDep, post_id: UUID):
    return await unlike_post_service(session, post_id, user)
