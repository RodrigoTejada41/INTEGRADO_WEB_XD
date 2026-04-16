from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class SyncRecord(Base):
    __tablename__ = 'sync_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('sync_batches.id'), index=True)
    record_key: Mapped[str] = mapped_column(String(120), index=True)
    record_type: Mapped[str] = mapped_column(String(80), index=True)
    event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    batch = relationship('SyncBatch', back_populates='records')
