from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class SyncBatch(Base):
    __tablename__ = 'sync_batches'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_batch_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    company_code: Mapped[str] = mapped_column(String(50), index=True)
    branch_code: Mapped[str] = mapped_column(String(50), index=True)
    terminal_code: Mapped[str] = mapped_column(String(50), index=True)
    source_ip: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default='success', index=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    records = relationship('SyncRecord', back_populates='batch', cascade='all, delete-orphan')
