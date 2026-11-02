from fastapi import APIRouter, status

from app.dependencies import SessionDep
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth import login_account, register_account

auth_router = APIRouter(tags=["auth"])


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
async def register(session: SessionDep, payload: UserCreate):
    return await register_account(session, payload)


@auth_router.post("/login", status_code=status.HTTP_200_OK, response_model=UserResponse)
async def login(session: SessionDep, payload: UserLogin):
    return await login_account(session, payload)
