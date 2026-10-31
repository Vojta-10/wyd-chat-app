from pydantic import SecretStr
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
