from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import ACCESS_COOKIE_NAME
from app.core.exceptions import InactiveAccount, InvalidToken
from app.models.user import User
from app.services.auth import get_user_from_access_token


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session = request.app.state.session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


SessionDep = Annotated[AsyncSession, Depends(get_db_session, scope="function")]

GetSettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    session: SessionDep,
    settings: GetSettingsDep,
    token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
) -> User:
    if token is None:
        raise InvalidToken()
    user = await get_user_from_access_token(session, token, settings.JWT_SECRET)
    return user


# TODO(test): optional auth (each case -> 200 on the feed, never 401/403)
#   - no cookie -> None
#   - garbage / expired / bad-signature token -> None
#   - valid token for a deleted user -> None
#   - valid token for an inactive user -> None (treated as anonymous)
#   - DB error during the lookup -> propagates as 500, NOT None (fail closed)
async def get_current_user_optional(
    session: SessionDep,
    settings: GetSettingsDep,
    token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
) -> User | None:
    if token is None:
        return None
    try:
        user = await get_user_from_access_token(session, token, settings.JWT_SECRET)
    except (InvalidToken, InactiveAccount):
        return None
    return user


type GetCurrentUserDep = Annotated[User, Depends(get_current_user)]
type GetCurrentUserOptionalDep = Annotated[
    User | None, Depends(get_current_user_optional)
]
