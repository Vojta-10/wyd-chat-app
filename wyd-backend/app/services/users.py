from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import update_user


async def update_user_fields(
    session: AsyncSession, user: User, payload: dict[str, Any]
) -> User:
    if not payload:
        return user
    await update_user(session, user, payload)
    return user
