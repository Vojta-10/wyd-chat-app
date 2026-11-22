import os
from pathlib import Path

import dotenv
import pytest
from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy.engine import make_url


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


# @pytest.fixture(name="session")
# async def session_fixture() -> AsyncGenerator:
#     engine = create_async_engine(
#         get_settings().DATABASE_URL_POOLING.get_secret_value(),
#         echo=True,
#         pool_pre_ping=True,
#         hide_parameters=True,
#     )
#     session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

#     try:
#         async with engine.connect() as conn:
#             await conn.execute(select(1))
#     except Exception:
#         await engine.dispose()
#         raise

#     session = session_factory()
#     try:
#         yield session
#         await session.commit()
#     except Exception:
#         await session.rollback()
#         raise
#     finally:
#         await session.close()
#     await engine.dispose()
