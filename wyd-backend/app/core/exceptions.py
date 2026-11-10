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


class UserNotFound(Exception):
    pass


async def user_not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": "User not found"}
    )
