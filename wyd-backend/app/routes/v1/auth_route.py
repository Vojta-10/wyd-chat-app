from fastapi import APIRouter, status

from app.dependencies import SessionDep
from app.schemas.user import UserCreate, UserResponse
from app.services.auth import register_account

auth_router = APIRouter()


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    tags=["auth"],
)
async def register(session: SessionDep, payload: UserCreate):
    return await register_account(session, payload)
