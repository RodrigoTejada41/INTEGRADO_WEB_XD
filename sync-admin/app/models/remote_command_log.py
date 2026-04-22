from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RemoteCommandLog(Base):
    __tablename__ = 'remote_command_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    command_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    command_type: Mapped[str] = mapped_column(String(80), index=True)
    origin: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    detail_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
