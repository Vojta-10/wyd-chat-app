from uuid import uuid7

from pytest import Subtests, mark
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from tests.helpers import ClientFactory, LoginUser, PostType, get_like_count


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
        like_count = await get_like_count(created_post.id, session)

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

    like_count = await get_like_count(created_post.id, session)

    post_fetch = await stranger.client.get(f"/v1/posts/{created_post.id}")
    assert post_fetch.status_code == 200

    assert post_fetch.json()["like_count"] == like_count
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
    assert second_like.json()["is_liked"] is True
    assert second_like.json()["like_count"] == 1

    like_count = await get_like_count(created_post.id, session)

    post_fetch = await stranger.client.get(f"/v1/posts/{created_post.id}")
    assert post_fetch.status_code == 200

    assert post_fetch.json()["like_count"] == like_count
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


async def test_post_like_not_logged_in(
    post: PostType, create_client: ClientFactory
) -> None:
    created_post, _ = post
    client = create_client()

    response = await client.put(f"/v1/posts/{created_post.id}/like")
    assert response.status_code == 401
