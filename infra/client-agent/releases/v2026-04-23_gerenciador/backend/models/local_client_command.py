from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utc_now


class LocalClientCommand(Base):
    __tablename__ = "local_client_commands"
    __table_args__ = (
        Index("ix_local_client_commands_client_status", "client_id", "status"),
        Index("ix_local_client_commands_empresa_id", "empresa_id"),
        Index("ix_local_client_commands_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("local_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    empresa_id: Mapped[str] = mapped_column(String(32), nullable=False)
    command_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    requested_by: Mapped[str] = mapped_column(String(120), nullable=False, default="system")
    origin: Mapped[str] = mapped_column(String(80), nullable=False, default="web")
    result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    delivered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
