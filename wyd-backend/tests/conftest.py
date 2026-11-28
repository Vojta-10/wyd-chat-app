import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from uuid import UUID

import dotenv
import pytest
from alembic.command import upgrade
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.dependencies import get_db_session
from tests.helpers import (
    TEST_PASSWORD,
    ClientFactory,
    LoginUser,
    UserResponse,
)


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


@pytest.fixture(name="session_override")
def session_override_fixture(session: AsyncSession) -> Generator[FastAPI]:
    from app.main import app

    async def get_session_override() -> AsyncSession:
        return session

    app.dependency_overrides[get_db_session] = get_session_override
    yield app
    app.dependency_overrides.clear()


@pytest.fixture(name="login")
async def login_user_fixture(
    create_client: ClientFactory,
) -> LoginUser:
    async def _login_user(
        *, username: str, password: str = TEST_PASSWORD, email: str
    ) -> UserResponse:

        client = create_client()
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
            client=client,
        )

    return _login_user


@pytest.fixture(name="create_client")
async def client_factory_fixture(
    session_override: FastAPI,
) -> AsyncGenerator[ClientFactory]:
    clients: list[AsyncClient] = []

    def _create_client() -> AsyncClient:

        client = AsyncClient(
            transport=ASGITransport(app=session_override), base_url="https://127.0.0.1"
        )
        clients.append(client)
        return client

    yield _create_client

    for client in clients:
        await client.aclose()
