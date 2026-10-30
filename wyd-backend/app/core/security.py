from anyio import CapacityLimiter, to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.exceptions import NotValidHashError

ph = PasswordHasher(time_cost=4, memory_cost=9216, parallelism=1)
limiter = CapacityLimiter(8)


async def hash_password(plain_password: str) -> str:
    return await to_thread.run_sync(ph.hash, plain_password, limiter=limiter)


async def verify_password(hashed_password: str, plain_password: str) -> bool:
    try:
        return bool(
            await to_thread.run_sync(
                ph.verify, hashed_password, plain_password, limiter=limiter
            )
        )
    except VerifyMismatchError:
        return False
    except InvalidHashError:
        raise NotValidHashError()
