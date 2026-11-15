from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import VARCHAR, CheckConstraint, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.uuidv7())
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(VARCHAR(128))

    user: Mapped["User"] = relationship(lazy="raise")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012

    __table_args__ = (
        Index(None, user_id, id),
        CheckConstraint("LENGTH(description) >= 1", name="description_length_check"),
    )
