from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import get_settings
from app.core.exceptions import (
    EmailAlreadyRegistered,
    InactiveAccount,
    InvalidCredentials,
    InvalidToken,
    UsernameTaken,
    email_already_registered_handler,
    inactive_account_handler,
    invalid_credentials_handler,
    invalid_token_handler,
    username_taken_handler,
)
from app.db.engine import initialize
from app.dependencies import SessionDep
from app.routes.v1.auth_route import auth_router
from app.routes.v1.users_route import users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    engine, session_factory = await initialize()
    app.state.session_factory = session_factory
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_methods=["GET", "POST"],
)

app.add_exception_handler(InvalidCredentials, invalid_credentials_handler)
app.add_exception_handler(EmailAlreadyRegistered, email_already_registered_handler)
app.add_exception_handler(UsernameTaken, username_taken_handler)
app.add_exception_handler(InactiveAccount, inactive_account_handler)
app.add_exception_handler(InvalidToken, invalid_token_handler)


@app.get("/")
async def root():
    return {"message": "Hello World!"}


@app.get("/health")
async def db_health(session: SessionDep):
    await session.execute(select(1))
    return {"message": "DB connection OK"}


app.include_router(auth_router, prefix="/v1/auth")
app.include_router(users_router, prefix="/v1/users")
