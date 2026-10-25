from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from app.db.engine import initialize
from app.dependencies import SessionDep


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    engine, session_factory = await initialize()
    app.state.session_factory = session_factory
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello World!"}


@app.get("/health")
async def db_health(session: SessionDep):
    await session.execute(select(1))
    return {"message": "DB connection OK"}
