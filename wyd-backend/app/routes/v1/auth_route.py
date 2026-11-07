from fastapi import APIRouter, Response, status

from app.core.constants import ACCESS_COOKIE_NAME
from app.dependencies import GetCurrentUserDep, GetSettingsDep, SessionDep
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
async def login(
    response: Response,
    session: SessionDep,
    payload: UserLogin,
    settings: GetSettingsDep,
):
    user, token = await login_account(
        session, payload, settings.JWT_ACCESS_TOKEN_LIFETIME, settings.JWT_SECRET
    )
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.JWT_ACCESS_TOKEN_LIFETIME
        * 60,  # max_age parameter in seconds, our env in minutes therefore * 60 to get seconds
    )
    return user

