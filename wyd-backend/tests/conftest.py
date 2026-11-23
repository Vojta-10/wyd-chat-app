import os
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import UUID

import dotenv
import pytest
from alembic.command import upgrade
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.constants import ACCESS_COOKIE_NAME
from app.dependencies import get_db_session
from tests.helpers import TEST_PASSWORD, LoginUser, UserResponse


def pytest_configure(config: pytest.Config) -> None:
    db_url = dotenv.get_key(f"{Path(__file__).parents[1]}/.env", "TEST_DATABASE_URL")
    if db_url is None:
        pytest.exit("Database url is none")
    real_url = make_url(db_url)
    if (
        real_url.host != "localhost" and real_url.host != "127.0.0.1"
    ) or real_url.database != "db_testing":
        pytest.exit("Database url doesn't match expected database url")
    os.environ["DATABASE_URL_POOLING"] = db_url
    os.environ["DATABASE_URL_NO_POOLING"] = db_url
    os.environ["TLS"] = "false"
    alembic_cfg = Config(f"{Path(__file__).parents[1]}/alembic.ini")
    upgrade(alembic_cfg, "heads")


@pytest.fixture(name="session")
async def session_fixture() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(
        get_settings().DATABASE_URL_POOLING.get_secret_value(),
        echo=True,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
    except Exception:
        await engine.dispose()
        raise

    session = session_factory()

    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
    await engine.dispose()


@pytest.fixture(name="client")
async def client_fixture(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    from app.main import app

    async def get_session_override() -> AsyncSession:
        return session

    app.dependency_overrides[get_db_session] = get_session_override
    client = AsyncClient(transport=ASGITransport(app=app), base_url="https://127.0.0.1")
    yield client
    app.dependency_overrides.clear()
    await client.aclose()


@pytest.fixture(name="login")
async def login_user_fixture(
    client: AsyncClient,
) -> LoginUser:
    async def _login_user(
        *, username: str, password: str = TEST_PASSWORD, email: str
    ) -> UserResponse:
        register = await client.post(
            "/v1/auth/register",
            json={"username": username, "password": password, "email": email},
        )
        assert register.status_code == 201
        user = await client.post(
            "/v1/auth/login", json={"password": password, "email": email}
        )
        assert user.status_code == 200
        response = await client.get("/v1/users/me")
        assert response.status_code == 200
        return UserResponse(
            username=response.json()["username"],
            id=UUID(response.json()["id"]),
            cookie=user.cookies[ACCESS_COOKIE_NAME],
        )

    return _login_user
