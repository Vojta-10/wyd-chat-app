from fastapi import Request, status
from fastapi.responses import JSONResponse


class NotValidHashError(Exception):
    pass


async def not_valid_hash_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Invalid credentials"},
    )
