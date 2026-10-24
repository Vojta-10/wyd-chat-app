from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL_POOLING: SecretStr
    DATABASE_URL_NO_POOLING: SecretStr
    ENVIRONMENT: Literal["dev", "prod"]

    model_config = SettingsConfigDict(env_file=f"{Path(__file__).parents[2]}/.env")


@lru_cache
def get_settings():
    return Settings()  # type: ignore
