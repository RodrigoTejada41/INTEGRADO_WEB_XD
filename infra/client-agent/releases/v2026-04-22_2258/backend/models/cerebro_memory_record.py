from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import utc_now
from backend.models.memory_base import MemoryBase


class CerebroMemoryRecord(MemoryBase):
    __tablename__ = "cerebro_vivo_memory"

    project_tag: Mapped[str] = mapped_column(String(120), primary_key=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_priority: Mapped[str] = mapped_column(String(32), nullable=False, default="API>DB>JSON")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class CerebroMemoryHistory(MemoryBase):
    __tablename__ = "cerebro_vivo_memory_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_tag: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="api")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

