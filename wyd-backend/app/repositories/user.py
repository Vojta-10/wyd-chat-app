from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_user(
    session: AsyncSession,
    hashed_password: SecretStr,
    *,
    username: str,
    email: str,
) -> User:
    new_user = User(
        username=username,
        hashed_password=hashed_password.get_secret_value(),
        email=email,
    )
    session.add(new_user)
    await session.flush()
    return new_user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(func.lower(User.email) == func.lower(email))
    )
    user = result.scalar_one_or_none()
    return user


async def update_user_hash(
    session: AsyncSession, user: User, new_hashed_password: str
) -> None:
    user.hashed_password = new_hashed_password
    await session.flush()


async def get_user_by_id(session: AsyncSession, user_id: str) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
