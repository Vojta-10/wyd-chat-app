from datetime import UTC, datetime, timedelta
from uuid import uuid7

from pytest import mark
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.schemas.post import PostPublic
from tests.helpers import LoginUser, PostType


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
