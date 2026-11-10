from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    InactiveAccount,
    InvalidCredentials,
    InvalidToken,
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


# TODO(test): register
#   - happy path: 201, body is only id + username (no email, no hash)
#   - email taken, different case (Bob@x.io vs bob@x.io) -> 409
#   - username taken, different case (Bob vs bob) -> 409
#   - race: two concurrent registers, same username -> one 201, one 409 (no 500)
#   - validation: password 11 or 129 chars -> 422; bad username chars -> 422
#   - mass assignment: extra field (is_active, id) -> 422
async def register_account(session: AsyncSession, payload: UserCreate) -> User:
    hashed_password: str = await hash_password(payload.password.get_secret_value())
    return await create_user(
        session,
        SecretStr(hashed_password),
        username=payload.username,
        email=payload.email,
    )


# TODO(test): login
#   - happy path: 200 + cookie with Secure, HttpOnly, SameSite=Strict, Path=/
#   - email lookup is case-insensitive (register bob@x.io, log in as BOB@x.io)
#   - enumeration: unknown email and wrong password -> identical 401 body
#   - enumeration timing: unknown-email path still runs a hash
#   - inactive + correct password -> 403; inactive + wrong password -> 401
#   - rehash: a hash made with old Argon2 params is upgraded after login
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


# TODO(test): access token -> user (security regression, all expect 401)
#   - no cookie / expired / bad signature / wrong iss / wrong aud
#   - missing a required claim (exp, iss, sub, iat, jti)
#   - alg confusion: token signed with "none" or another algorithm
#   - valid token for a user that no longer exists
#   - valid signature but sub is not a valid UUID
#   - and: valid token for an inactive user -> 403
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
