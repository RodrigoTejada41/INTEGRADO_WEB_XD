from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserBranchPermission(Base):
    __tablename__ = "user_branch_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "empresa_id", "branch_code", name="uq_user_branch_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    empresa_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    branch_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    can_view_reports: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
