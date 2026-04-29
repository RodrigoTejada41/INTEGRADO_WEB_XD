from __future__ import annotations

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from backend.models.produto_de_para import ProdutoDePara
from backend.models.venda import Venda


class ProdutoDeParaRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, *, empresa_id: str, mapping_id: int) -> ProdutoDePara | None:
        return (
            self.session.query(ProdutoDePara)
            .filter(ProdutoDePara.empresa_id == empresa_id, ProdutoDePara.id == mapping_id)
            .one_or_none()
        )

    def get_by_local_code(self, *, empresa_id: str, codigo_produto_local: str) -> ProdutoDePara | None:
        return (
            self.session.query(ProdutoDePara)
            .filter(
                ProdutoDePara.empresa_id == empresa_id,
                ProdutoDePara.codigo_produto_local == codigo_produto_local,
            )
            .one_or_none()
        )

    def list(
        self,
        *,
        empresa_id: str,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProdutoDePara]:
        query = self.session.query(ProdutoDePara).filter(ProdutoDePara.empresa_id == empresa_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                ProdutoDePara.codigo_produto_local.ilike(term)
                | ProdutoDePara.codigo_produto_web.ilike(term)
                | ProdutoDePara.descricao_produto_local.ilike(term)
                | ProdutoDePara.descricao_produto_web.ilike(term)
            )
        return (
            query.order_by(ProdutoDePara.codigo_produto_local.asc(), ProdutoDePara.id.asc())
            .offset(max(offset, 0))
            .limit(max(1, min(limit, 500)))
            .all()
        )

    def upsert_by_local_code(self, *, empresa_id: str, values: dict[str, object]) -> ProdutoDePara:
        codigo_produto_local = str(values["codigo_produto_local"])
        existing = self.get_by_local_code(
            empresa_id=empresa_id,
            codigo_produto_local=codigo_produto_local,
        )
        if existing is None:
            existing = ProdutoDePara(empresa_id=empresa_id, **values)
            self.session.add(existing)
            self.session.flush()
            return existing

        for field, value in values.items():
            if field in {"empresa_id", "codigo_produto_local"}:
                continue
            setattr(existing, field, value)
        self.session.flush()
        return existing

    def update(self, mapping: ProdutoDePara, values: dict[str, object]) -> ProdutoDePara:
        for field, value in values.items():
            if value is not None:
                setattr(mapping, field, value)
        self.session.flush()
        return mapping

    def delete(self, mapping: ProdutoDePara) -> None:
        self.session.delete(mapping)
        self.session.flush()

    def list_unmapped_products(self, *, empresa_id: str, limit: int = 100) -> list[dict[str, object]]:
        join_condition = and_(
            ProdutoDePara.empresa_id == Venda.empresa_id,
            ProdutoDePara.codigo_produto_local == Venda.codigo_produto_local,
        )
        stmt: Select = (
            select(
                Venda.codigo_produto_local.label("codigo_produto_local"),
                func.max(Venda.produto).label("descricao_produto_local"),
                func.max(Venda.familia_produto).label("familia_local"),
                func.max(Venda.categoria_produto).label("categoria_local"),
                func.count(Venda.id).label("vendas_count"),
            )
            .outerjoin(ProdutoDePara, join_condition)
            .where(
                Venda.empresa_id == empresa_id,
                Venda.codigo_produto_local.is_not(None),
                Venda.codigo_produto_local != "",
                ProdutoDePara.id.is_(None),
            )
            .group_by(Venda.codigo_produto_local)
            .order_by(func.count(Venda.id).desc(), Venda.codigo_produto_local.asc())
            .limit(max(1, min(limit, 500)))
        )
        return [dict(row._mapping) for row in self.session.execute(stmt).all()]
