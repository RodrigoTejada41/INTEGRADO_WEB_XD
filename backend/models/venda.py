from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utc_now


class Venda(Base):
    __tablename__ = "vendas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "uuid", name="uq_vendas_empresa_uuid"),
        Index("ix_vendas_empresa_data", "empresa_id", "data"),
        Index("ix_vendas_empresa_data_atualizacao", "empresa_id", "data_atualizacao"),
        Index("ix_vendas_empresa_codigo_produto", "empresa_id", "codigo_produto_local"),
        Index("ix_vendas_empresa_terminal", "empresa_id", "terminal_code"),
        Index("ix_vendas_empresa_pagamento", "empresa_id", "forma_pagamento"),
        Index("ix_vendas_empresa_familia", "empresa_id", "familia_produto"),
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
    bandeira_cartao: Mapped[str | None] = mapped_column(String(80), nullable=True)
    familia_produto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    categoria_produto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    codigo_produto_local: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    operador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cliente: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status_venda: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cancelada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    produto: Mapped[str] = mapped_column(String(255), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("1"))
    valor_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    valor_bruto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    desconto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    acrescimo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    valor_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
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
    bandeira_cartao: Mapped[str | None] = mapped_column(String(80), nullable=True)
    familia_produto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    categoria_produto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    codigo_produto_local: Mapped[str | None] = mapped_column(String(120), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    operador: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cliente: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status_venda: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cancelada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    produto: Mapped[str] = mapped_column(String(255), nullable=False)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=Decimal("1"))
    valor_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    valor_bruto: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    desconto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    acrescimo: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    valor_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arquivado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
