from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utc_now


class TenantAuditEvent(Base):
    __tablename__ = "tenant_audit_events"
    __table_args__ = (
        Index("ix_tenant_audit_events_empresa_id", "empresa_id"),
        Index("ix_tenant_audit_events_created_at", "created_at"),
        Index("ix_tenant_audit_events_action", "action"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="success")
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
