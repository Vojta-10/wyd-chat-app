from datetime import UTC, datetime, timedelta
from typing import Literal, assert_never
from uuid import uuid7

import httpx
from pytest import Subtests, mark
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AllowedPostsVisibility
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.user import User
from app.schemas.post import PostPublic
from tests.helpers import ClientFactory, LoginUser, PostType, UserResponse


@mark.parametrize(
    "block_direction",
    [
        ("owner_blocked"),
        ("blocked_owner"),
    ],
)
@mark.parametrize(
    "visibility_setting, expected_status_code_get, expected_status_code_patch_delete",
    [("everybody", 200, 403), ("logged-in", 404, 403), ("nobody", 404, 404)],
)
async def test_posts_methods(
    subtests: Subtests,
    login: LoginUser,
    create_client: ClientFactory,
    block_direction: str,
    visibility_setting: AllowedPostsVisibility,
    expected_status_code_get: int,
    expected_status_code_patch_delete: int,
) -> None:
    # User Creations
    owner = await login(username="Owner123", email="owner@example.com")
    stranger = await login(username="Stranger123", email="stranger@example.com")
    blocked_user = await login(username="Blocked123", email="blocked@example.com")
    anonymous = create_client()

    # Post visibility setting
    visibility_body = {"visibility": visibility_setting}
    update_visibility = await owner.client.patch(
        "/v1/users/me/profile", json=visibility_body
    )
    assert update_visibility.status_code == 200
    assert update_visibility.json()["visibility"] == visibility_setting
    # Post Creation
    post = await owner.client.post("/v1/posts/", json={"description": "Ahoj123"})
    assert post.status_code == 201
    post_id = post.json()["id"]
    # Block
    if block_direction == "owner_blocked":
        block = await owner.client.put(f"/v1/users/{blocked_user.username}/block")
        assert block.status_code == 204
    else:
        block = await blocked_user.client.put(f"/v1/users/{owner.username}/block")
        assert block.status_code == 204

    table_data: list[
        tuple[
            UserResponse | httpx.AsyncClient,
            str,
            int,
            Literal["unchanged", "changed", "deleted"],
        ]
    ] = [
        (
            stranger,
            "GET",
            expected_status_code_get if visibility_setting == "nobody" else 200,
            "unchanged",
        ),
        (stranger, "PATCH", expected_status_code_patch_delete, "unchanged"),
        (stranger, "DELETE", expected_status_code_patch_delete, "unchanged"),
        (blocked_user, "GET", 404, "unchanged"),
        (blocked_user, "PATCH", 404, "unchanged"),
        (blocked_user, "DELETE", 404, "unchanged"),
        (anonymous, "GET", expected_status_code_get, "unchanged"),
        (anonymous, "PATCH", 401, "unchanged"),
        (anonymous, "DELETE", 401, "unchanged"),
        (owner, "GET", 200, "unchanged"),
        (owner, "PATCH", 200, "changed"),
        (owner, "DELETE", 204, "deleted"),
    ]

    for client, method, expected_status_code, outcome in table_data:
        with subtests.test(
            msg=f"{
                client.username if isinstance(client, UserResponse) else 'anonymous'
            } {method}",
        ):
            body = None
            if method == "PATCH":
                body = {"description": "ahojda123"}
            if isinstance(client, UserResponse):
                response = await client.client.request(
                    method=method, url=f"/v1/posts/{post_id}", json=body
                )
            else:
                response = await client.request(
                    method=method, url=f"/v1/posts/{post_id}", json=body
                )
            assert response.status_code == expected_status_code

            if method == "PATCH" or method == "DELETE":
                refetch = await owner.client.request(
                    method="GET", url=f"/v1/posts/{post_id}"
                )
                if outcome == "unchanged":
                    assert refetch.json() == post.json()
                elif outcome == "changed":
                    assert body
                    assert refetch.json()["description"] == body["description"]
                elif outcome == "deleted":
                    assert refetch.status_code == 404
                else:
                    assert_never(outcome)


async def test_create_new_post_not_logged_in(create_client: ClientFactory) -> None:
    client = create_client()
    response = await client.post("/v1/posts/", json={"description": "Not logged in"})
    assert response.status_code == 401


async def test_create_new_post_extra_field_in_body(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post(
        "/v1/posts/", json={"description": "Extra field", "user_id": "123"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


@mark.parametrize(
    "description_value, error_type",
    [
        (None, "string_type"),
        ("", "string_too_short"),
        ("      ", "string_too_short"),
        ("a" * 257, "string_too_long"),
        ("ahoj\rhehe", "value_error"),
    ],
)
async def test_create_new_post_invalid_description(
    login: LoginUser, description_value: str | None, error_type: str
) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post(
        "/v1/posts/", json={"description": description_value}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == error_type


async def test_create_new_post_description_missing(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post("/v1/posts/", json={})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body", "description"]


async def test_create_new_post_new_line_normalize(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post(
        "/v1/posts/", json={"description": "ahoj\nahoj\r\nahoj"}
    )
    assert response.status_code == 201
    assert response.json()["description"] == "ahoj\nahoj\nahoj"


async def test_create_new_post(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post("/v1/posts/", json={"description": "a" * 256})
    assert response.status_code == 201
    post = response.json()
    assert post["description"] == "a" * 256
    assert post["author"]["username"] == user.username
    assert post["author"]["display_name"] == user.username
    assert post["like_count"] == 0
    assert post["is_liked"] is False


async def test_patch_post_unknown_id(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")

    patch_unknown = await user.client.patch(
        f"/v1/posts/{uuid7()}", json={"description": "ahoj 132"}
    )
    assert patch_unknown.status_code == 404


async def test_patch_description_null(post: PostType) -> None:
    created_post, user = post
    response = await user.client.patch(
        f"/v1/posts/{created_post.id}", json={"description": None}
    )
    assert response.status_code == 422
    refetched_post = await user.client.get(f"/v1/posts/{created_post.id}")
    assert refetched_post.status_code == 200
    assert (
        refetched_post.json()["description"] == created_post.model_dump()["description"]
    )


async def test_patch_empty_body(post: PostType) -> None:
    created_post, user = post
    response = await user.client.patch(f"/v1/posts/{created_post.id}", json={})
    assert response.status_code == 200
    refetched_post = await user.client.get(f"/v1/posts/{created_post.id}")
    assert refetched_post.status_code == 200
    assert (
        refetched_post.json()["description"] == created_post.model_dump()["description"]
    )


async def test_patch_updated_at_moves_like_count_created_at_unchanged(
    post: PostType, session: AsyncSession
) -> None:
    created_post, user = post
    await session.execute(
        update(Post)
        .where(Post.id == created_post.id)
        .values(updated_at=(datetime.now(UTC) - timedelta(days=3)), like_count=1)
    )
    time_updated_post = await user.client.get(f"/v1/posts/{created_post.id}")
    assert time_updated_post.status_code == 200
    response = await user.client.patch(
        f"/v1/posts/{created_post.id}", json={"description": "updated description"}
    )
    assert response.status_code == 200
    validated_post = PostPublic.model_validate(time_updated_post.json())
    validated_response = PostPublic.model_validate(response.json())
    assert validated_response.updated_at > validated_post.updated_at
    assert validated_response.like_count == validated_post.like_count
    assert validated_response.created_at == validated_post.created_at
    assert validated_response.description == "updated description"


@mark.parametrize(
    "attribute, value",
    [("id", str(uuid7())), ("user_id", str(uuid7())), ("like_count", 1000)],
)
async def test_patch_post_mass_assignment(
    post: PostType, attribute: str, value: str | int
) -> None:
    created_post, user = post
    response = await user.client.patch(
        f"/v1/posts/{created_post.id}",
        json={"description": "Updated Example", attribute: value},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"
    assert response.json()["detail"][0]["loc"] == ["body", attribute]


@mark.parametrize("block_direction", ["owner_to_stranger", "stranger_to_owner"])
async def test_post_like_blocked(
    post: PostType, login: LoginUser, block_direction: str
) -> None:
    created_post, owner = post
    stranger = await login(username="Vojta123", email="vojta123@example.com")

    if block_direction == "owner_to_stranger":
        block = await owner.client.put(f"/v1/users/{stranger.username}/block")
        assert block.status_code == 204
    elif block_direction == "stranger_to_owner":
        block = await stranger.client.put(f"/v1/users/{owner.username}/block")
        assert block.status_code == 204

    like_response = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
    assert like_response.status_code == 404
    assert like_response.json()["detail"] == "Post not found"

    refetch = await owner.client.get(f"/v1/posts/{created_post.id}")
    assert refetch.json()["like_count"] == created_post.like_count


async def test_post_like_visibility_nobody(post: PostType, login: LoginUser) -> None:
    created_post, owner = post
    stranger = await login(username="Vojta123", email="vojta123@example.com")

    set_visibility = await owner.client.patch(
        "/v1/users/me/profile", json={"visibility": "nobody"}
    )

    assert set_visibility.status_code == 200

    like_response = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
    assert like_response.status_code == 404
    assert like_response.json()["detail"] == "Post not found"

    refetch = await owner.client.get(f"/v1/posts/{created_post.id}")
    assert refetch.json()["like_count"] == created_post.like_count


async def test_post_like_unknown_post_inactive_author(
    post: PostType, login: LoginUser, subtests: Subtests, session: AsyncSession
) -> None:
    created_post, user = post
    stranger = await login(username="Vojta123", email="vojta123@example.com")
    with subtests.test(msg="Like on unknown post"):
        unknown_post = await stranger.client.put(f"/v1/posts/{uuid7()}/like")
        assert unknown_post.status_code == 404
        assert unknown_post.json()["detail"] == "Post not found"
        refetch = await user.client.get(f"/v1/posts/{created_post.id}")
        assert refetch.status_code == 200
        assert refetch.json()["like_count"] == created_post.like_count

    with subtests.test(msg="Like on post with inactive author"):
        await session.execute(
            update(User).where(User.id == user.id).values(is_active=False)
        )
        inactive_author = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
        assert inactive_author.status_code == 404
        assert inactive_author.json()["detail"] == "Post not found"
        like_count = await session.scalar(
            select(func.count(PostLike.post_id)).where(
                PostLike.post_id == created_post.id
            )
        )
        assert like_count is not None
        assert like_count == created_post.like_count


async def test_post_like_happy_path(
    post: PostType, login: LoginUser, session: AsyncSession
) -> None:
    created_post, _ = post
    stranger = await login(username="Vojta123", email="vojta123@example.com")

    like = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
    assert like.status_code == 200
    assert like.json()["is_liked"] is True
    assert like.json()["like_count"] == 1

    refetch = await stranger.client.get(f"/v1/posts/{created_post.id}")
    assert refetch.status_code == 200

    assert refetch.json()["is_liked"] is True

    like_count = await session.scalar(
        select(func.count(PostLike.post_id)).where(PostLike.post_id == created_post.id)
    )

    post_fetch = await stranger.client.get(f"/v1/posts/{created_post.id}")
    assert post_fetch.status_code == 200

    assert post_fetch.json()["like_count"] == like_count
    assert like_count is not None
    assert like_count == 1


async def test_post_like_twice(
    post: PostType, login: LoginUser, session: AsyncSession
) -> None:
    created_post, _ = post
    stranger = await login(username="Vojta123", email="vojta123@example.com")

    first_like = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
    assert first_like.status_code == 200
    assert first_like.json()["is_liked"] is True
    assert first_like.json()["like_count"] == 1

    second_like = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
    assert second_like.status_code == 200
    assert first_like.json()["is_liked"] is True
    assert first_like.json()["like_count"] == 1

    like_count = await session.scalar(
        select(func.count(PostLike.post_id)).where(PostLike.post_id == created_post.id)
    )

    post_fetch = await stranger.client.get(f"/v1/posts/{created_post.id}")
    assert post_fetch.status_code == 200

    assert post_fetch.json()["like_count"] == like_count
    assert like_count is not None
    assert like_count == 1


async def test_post_like_a_like_doesnt_make_b_is_liked_true(
    post: PostType, login: LoginUser
) -> None:
    created_post, owner = post
    stranger = await login(username="Vojta123", email="vojta123@example.com")

    first_like = await stranger.client.put(f"/v1/posts/{created_post.id}/like")
    assert first_like.status_code == 200

    stranger_fetch = await stranger.client.get(f"/v1/posts/{created_post.id}")
    assert stranger_fetch.status_code == 200
    assert stranger_fetch.json()["is_liked"] is True

    owner_fetch = await owner.client.get(f"/v1/posts/{created_post.id}")
    assert owner_fetch.status_code == 200
    assert owner_fetch.json()["is_liked"] is False
