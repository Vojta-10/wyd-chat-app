from typing import TYPE_CHECKING, get_args
from uuid import UUID

from sqlalchemy import VARCHAR, CheckConstraint, ForeignKey, column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import AllowedThemes
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(VARCHAR(64))
    bio: Mapped[str] = mapped_column(VARCHAR(128), server_default="")
    pronouns: Mapped[str] = mapped_column(VARCHAR(16), server_default="")
    theme: Mapped[str] = mapped_column(VARCHAR, server_default="system")
    accent_color: Mapped[str | None] = mapped_column(VARCHAR)

    user: Mapped["User"] = relationship(back_populates="user_profile")

    __table_args__ = (
        CheckConstraint(
            column("theme").in_(get_args(AllowedThemes)),
            name="allowed_theme",
        ),
        CheckConstraint(
            "accent_color ~ '^#[0-9A-F]{6}$'", name="accent_color_hex_format"
        ),
    )
