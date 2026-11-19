from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, column, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserBlock(Base):
    __tablename__ = "user_blocks"

    blocker_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            column("blocker_id") != (column("blocked_id")), name="self_block_guard"
        ),
    )
