from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from app.schemas.user_profile import UserProfilePublicBase, UserProfileSelfBase

# TODO(M2): reserved usernames, checked case-insensitively on register and PATCH.
#   Route words that would shadow /users/{username} (search, settings, blocked...)
#   plus impersonation names (admin, support, wyd...). Decide before M2 adds the
#   first /users/<word> route.
username_constraint = Field(min_length=5, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class UserBase(BaseModel):
    username: Annotated[str, username_constraint]


class UserAuthBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(max_length=128)
    email: EmailStr = Field(max_length=254)


class UserCreate(UserBase, UserAuthBase):
    password: SecretStr = Field(min_length=12, max_length=128)


class UserLogin(UserAuthBase):
    pass


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    created_at: datetime


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    username: str
    user_profile: UserProfilePublicBase | None


class UserSelf(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    username: str
    user_profile: UserProfileSelfBase | None


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Annotated[str | None, username_constraint] = None

    @field_validator("username", mode="before")
    @classmethod
    def reject_explicit_null(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Username must not be null")
        return v
