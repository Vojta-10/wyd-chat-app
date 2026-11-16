from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StringConstraints,
    field_validator,
)

from app.utils.validations import reject_control_chars


def normalize_new_lines(v: Any) -> Any:
    if isinstance(v, str):
        v = v.replace("\r\n", "\n")
    return v


type Description = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
    reject_control_chars(frozenset("\n")),
    BeforeValidator(normalize_new_lines),
]


class PostBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PostUser(BaseModel):
    username: str
    display_name: str
    accent_color: str | None
    pronouns: str


class PostPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    author: PostUser
    description: str
    like_count: int
    is_liked: bool
    created_at: datetime
    updated_at: datetime


class PostCreate(PostBase):
    description: Description


class PostPatch(PostBase):
    description: Description | None = None

    @field_validator("description", mode="before")
    @classmethod
    def enforce_non_null_description(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Description must not be null")
        return v
