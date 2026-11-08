import uuid
from datetime import UTC, datetime, timedelta

from anyio import CapacityLimiter, to_thread
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jwt import InvalidTokenError, decode, encode
from pydantic import SecretStr

from app.core.exceptions import InvalidToken

ph = PasswordHasher(time_cost=4, memory_cost=9216, parallelism=1)
limiter = CapacityLimiter(8)
from app.core.constants import ACCESS_TOKEN_AUDIENCE, ISSUER

JWT_ENCODING_ALGORITHM = "HS256"


async def hash_password(plain_password: str) -> str:
    return await to_thread.run_sync(ph.hash, plain_password, limiter=limiter)


def needs_rehash(hash: str) -> bool:
    return ph.check_needs_rehash(hash)


async def verify_password(hashed_password: str, plain_password: str) -> bool:
    try:
        return bool(
            await to_thread.run_sync(
                ph.verify, hashed_password, plain_password, limiter=limiter
            )
        )
    except VerifyMismatchError:
        return False


def create_access_token(
    user_id: str,
    jwt_access_token_lifetime: int,
    jwt_secret: SecretStr,
) -> str:
    now = datetime.now(UTC)
    jwt_body = {
        "sub": user_id,
        "iss": ISSUER,
        "aud": ACCESS_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=jwt_access_token_lifetime),
        "jti": str(uuid.uuid4()),
    }
    jwt_token = encode(
        payload=jwt_body,
        key=jwt_secret.get_secret_value(),
        algorithm=JWT_ENCODING_ALGORITHM,
    )
    return jwt_token


def decode_access_token(token: str, jwt_secret: SecretStr) -> str:
    try:
        payload = decode(
            jwt=token,
            key=jwt_secret.get_secret_value(),
            options={
                "require": ["exp", "iss", "sub", "iat", "jti"],
            },
            issuer=ISSUER,
            audience=ACCESS_TOKEN_AUDIENCE,
            algorithms=[JWT_ENCODING_ALGORITHM],
        )
        return payload["sub"]
    except InvalidTokenError:
        raise InvalidToken()
