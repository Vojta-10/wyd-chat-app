from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

TEST_PASSWORD = "secret123123"


@dataclass
class UserResponse:
    username: str
    id: UUID
    cookie: str


class LoginUser(Protocol):
    async def __call__(
        self, *, username: str, password: str = TEST_PASSWORD, email: str
    ) -> UserResponse: ...
