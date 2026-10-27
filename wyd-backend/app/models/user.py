import os
import sys
from datetime import datetime
from uuid import UUID

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(script_dir))


from db.base import Base
from sqlalchemy import Boolean, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.uuidv7())
    hashed_password: Mapped[str]
    email: Mapped[str] = mapped_column(String(254))
    username: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=expression.true())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(None, func.lower(email), unique=True),
        Index(None, func.lower(username), unique=True),
    )
