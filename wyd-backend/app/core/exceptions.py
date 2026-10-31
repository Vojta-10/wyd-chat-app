from fastapi import Request, status
from fastapi.responses import JSONResponse


class NotValidHashError(Exception):
    pass


async def not_valid_hash_error_handler(request: Request, exc: Exception):
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


