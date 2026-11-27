from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from httpx import AsyncClient

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
