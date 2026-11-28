from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post_like import PostLike
from app.schemas.post import PostPublic

TEST_PASSWORD = "secret123123"

type ClientFactory = Callable[[], AsyncClient]


type PostType = tuple[PostPublic, UserResponse]


@dataclass
class UserResponse:
    username: str
    id: UUID
    client: AsyncClient


class LoginUser(Protocol):
    async def __call__(
        self, *, username: str, password: str = TEST_PASSWORD, email: str
    ) -> UserResponse: ...


async def get_like_count(post_id: UUID, session: AsyncSession) -> int:
    like_count = await session.scalar(
        select(func.count(PostLike.post_id)).where(PostLike.post_id == post_id)
    )
    assert like_count is not None
    return like_count
