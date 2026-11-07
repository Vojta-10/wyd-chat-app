from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL_POOLING: SecretStr
    DATABASE_URL_NO_POOLING: SecretStr
    ENVIRONMENT: Literal["dev", "prod"]
    CORS_ORIGINS: list[str]
    JWT_SECRET: SecretStr = Field(min_length=43)
    JWT_ACCESS_TOKEN_LIFETIME: int = Field(ge=10, le=60)
    model_config = SettingsConfigDict(env_file=f"{Path(__file__).parents[2]}/.env")


@lru_cache
def get_settings():
    return Settings()  # type: ignore
