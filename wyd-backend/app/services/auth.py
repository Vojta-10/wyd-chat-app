from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmailAlreadyRegistered, UsernameTaken
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import create_user
from app.schemas.user import UserCreate


async def register_account(session: AsyncSession, payload: UserCreate) -> User:
    hashed_password: str = await hash_password(payload.password.get_secret_value())
    try:
        return await create_user(
            session,
            SecretStr(hashed_password),
            username=payload.username,
            email=payload.email,
        )
    except IntegrityError as e:
        dbapi_error = e.orig
        asyncpg_error = getattr(dbapi_error, "__cause__", None)

        constraint_name = getattr(asyncpg_error, "constraint_name", None)
        if constraint_name == "ix_users_email":
            raise EmailAlreadyRegistered()
        elif constraint_name == "ix_users_username":
            raise UsernameTaken()
        else:
            raise
