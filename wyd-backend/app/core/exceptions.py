from fastapi import Request, status
from fastapi.responses import JSONResponse


class InvalidCredentials(Exception):
    pass


async def invalid_credentials_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid credentials"},
    )


class EmailAlreadyRegistered(Exception):
    pass


async def email_already_registered_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Email already registered"},
    )


class UsernameTaken(Exception):
    pass


async def username_taken_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Username already in use"},
    )


class InactiveAccount(Exception):
    pass


async def inactive_account_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Account is inactive"}
    )


class InvalidToken(Exception):
    pass


async def invalid_token_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid token"},
    )


class DisallowedUpdateField(Exception):
    """A field outside the repository's update allowlist reached the DB layer.

    This is a bug in our code (the schema should have rejected it), not a client
    error, so it intentionally has NO exception handler and surfaces as a 500.
    """

    def __init__(self, field: str) -> None:
        # Only the field *name* goes into the message, never the value (may be PII).
        super().__init__(f"Field not allowed in user update: {field!r}")
        self.field = field


class UserProfileInsertError(Exception):
    """A user's profile row is still missing after the self-heal insert and re-read.

    The AFTER INSERT trigger on `users` should guarantee every user has a profile,
    and self-heal covers the rare case where it doesn't. Reaching this means even
    that failed, so it's an invariant violation on our side, not a client error.
    It intentionally has NO exception handler and surfaces as a 500.
    """


class UserNotFound(Exception):
    pass


async def user_not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "User not found"}
    )
