import ssl

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


async def initialize() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    in_dev: bool = get_settings().ENVIRONMENT == "dev"
    engine = create_async_engine(
        get_settings().DATABASE_URL_POOLING.get_secret_value(),
        # TODO(security): echo logs bound parameters, so emails and Argon2 hashes
        #   show up in the dev terminal. README gap scheduled for M6: fix or
        #   reschedule before tagging v0.1.0.
        echo=in_dev,
        connect_args={
            "ssl": ssl.create_default_context(),
        },
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
    except Exception:
        await engine.dispose()
        raise
    return engine, session_factory
