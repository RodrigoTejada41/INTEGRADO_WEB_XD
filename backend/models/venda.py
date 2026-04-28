from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utc_now


class Venda(Base):
    __tablename__ = "vendas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "uuid", name="uq_vendas_empresa_uuid"),
        Index("ix_vendas_empresa_data", "empresa_id", "data"),
        Index("ix_vendas_empresa_data_atualizacao", "empresa_id", "data_atualizacao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(128), nullable=False)
    empresa_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tenants.empresa_id", ondelete="RESTRICT"), nullable=False
    )
    branch_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    terminal_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_venda: Mapped[str | None] = mapped_column(String(80), nullable=True)
    forma_pagamento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    familia_produto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    produto: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class VendaHistorico(Base):
    __tablename__ = "vendas_historico"
    __table_args__ = (
        Index("ix_vendas_hist_empresa_data", "empresa_id", "data"),
        Index("ix_vendas_hist_arquivado_em", "arquivado_em"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(128), nullable=False)
    empresa_id: Mapped[str] = mapped_column(String(32), nullable=False)
    branch_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    terminal_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tipo_venda: Mapped[str | None] = mapped_column(String(80), nullable=True)
    forma_pagamento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    familia_produto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    produto: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arquivado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
