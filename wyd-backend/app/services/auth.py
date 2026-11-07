from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmailAlreadyRegistered,
    InactiveAccount,
    InvalidCredentials,
    InvalidToken,
    UsernameTaken,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.repositories.user import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user_hash,
)
from app.schemas.user import UserCreate, UserLogin


# TODO: Tests
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


# TODO: Tests
async def login_account(
    session: AsyncSession,
    payload: UserLogin,
    jwt_token_lifetime: int,
    jwt_secret: SecretStr,
) -> tuple[User, str]:
    user = await get_user_by_email(session, payload.email)

    if user is None:
        await hash_password("dummy-password-hash")
        raise InvalidCredentials()

    if not await verify_password(
        user.hashed_password, payload.password.get_secret_value()
    ):
        raise InvalidCredentials()

    if not user.is_active:
        raise InactiveAccount()

    if needs_rehash(user.hashed_password):
        new_hash: str = await hash_password(payload.password.get_secret_value())
        await update_user_hash(session, user, new_hash)

    token = create_access_token(str(user.id), jwt_token_lifetime, jwt_secret)

    return user, token


async def get_user_from_access_token(
    session: AsyncSession, token: str, jwt_secret: SecretStr
) -> User:
    user_id = decode_access_token(token=token, jwt_secret=jwt_secret)
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise InvalidToken()

    if not user.is_active:
        raise InactiveAccount()

    return user
