from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.engine import get_db_session

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]

GetSettingsDep = Annotated[Settings, Depends(get_settings)]
