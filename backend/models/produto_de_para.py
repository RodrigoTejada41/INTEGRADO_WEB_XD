from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utc_now


class ProdutoDePara(Base):
    __tablename__ = "produto_de_para"
    __table_args__ = (
        UniqueConstraint("empresa_id", "codigo_produto_local", name="uq_produto_de_para_empresa_codigo_local"),
        Index("ix_produto_de_para_empresa_codigo_local", "empresa_id", "codigo_produto_local"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tenants.empresa_id", ondelete="CASCADE"), nullable=False
    )
    cnpj: Mapped[str] = mapped_column(String(32), nullable=False)
    codigo_produto_local: Mapped[str] = mapped_column(String(120), nullable=False)
    codigo_produto_web: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descricao_produto_local: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descricao_produto_web: Mapped[str | None] = mapped_column(String(255), nullable=True)
    familia_local: Mapped[str | None] = mapped_column(String(160), nullable=True)
    familia_web: Mapped[str | None] = mapped_column(String(160), nullable=True)
    categoria_local: Mapped[str | None] = mapped_column(String(160), nullable=True)
    categoria_web: Mapped[str | None] = mapped_column(String(160), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
