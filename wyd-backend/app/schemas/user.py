from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr


class UserBase(BaseModel):
    username: str = Field(min_length=5, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=12, max_length=128)
    email: EmailStr = Field(max_length=254)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class UserSelf(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    created_at: datetime
    updated_at: datetime
