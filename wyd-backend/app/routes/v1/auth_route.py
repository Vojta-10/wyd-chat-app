from fastapi import APIRouter, Response, status

from app.core.constants import ACCESS_COOKIE_NAME, AUTH_COOKIE_OPTIONS
from app.dependencies import GetSettingsDep, SessionDep
from app.schemas.user import UserCreate, UserLogin, UserPublic
from app.services.auth import login_account, register_account

auth_router = APIRouter(tags=["auth"])


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserPublic,
)
async def register(session: SessionDep, payload: UserCreate):
    return await register_account(session, payload)


@auth_router.post("/login", status_code=status.HTTP_200_OK, response_model=UserPublic)
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
        max_age=settings.JWT_ACCESS_TOKEN_LIFETIME
        * 60,  # max_age parameter in seconds, our env in minutes therefore * 60 to get seconds
        **AUTH_COOKIE_OPTIONS,
    )
    return user


# TODO(test): logout
#   - Set-Cookie clears the cookie: same name, Max-Age=0, Path=/, Secure
#   - after logout, a request without the cookie to /users/me -> 401
@auth_router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    response.delete_cookie(key=ACCESS_COOKIE_NAME, **AUTH_COOKIE_OPTIONS)
    return {"detail": "Successfully logged out"}
