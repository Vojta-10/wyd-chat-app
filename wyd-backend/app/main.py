from fastapi import FastAPI
from sqlalchemy import select

from app.dependencies import SessionDep

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World!"}


@app.get("/health")
async def db_health(session: SessionDep):
    await session.execute(select(1))
    return {"message": "DB connection OK"}
