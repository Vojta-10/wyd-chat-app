import pytest

from app.schemas.post import PostPublic
from tests.helpers import LoginUser, PostType


@pytest.fixture(name="post")
async def create_post_fixture(login: LoginUser) -> PostType:
    user = await login(username="Vojta", email="vojta@example.com")

    created_post = await user.client.post(
        "/v1/posts/", json={"description": "Example post"}
    )
    assert created_post.status_code == 201
    post = created_post.json()
    return PostPublic.model_validate(post), user
