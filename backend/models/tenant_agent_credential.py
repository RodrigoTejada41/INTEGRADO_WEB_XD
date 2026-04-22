from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utc_now


class TenantAgentCredential(Base):
    __tablename__ = "tenant_agent_credentials"
    __table_args__ = (
        Index("ix_tenant_agent_credentials_empresa_id", "empresa_id"),
        Index("ix_tenant_agent_credentials_active", "active"),
        Index("ix_tenant_agent_credentials_last_used_at", "last_used_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    empresa_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("tenants.empresa_id", ondelete="CASCADE"),
        nullable=False,
    )
    device_label: Mapped[str] = mapped_column(String(120), nullable=False, default="local-agent")
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
