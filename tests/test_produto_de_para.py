from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base
from backend.models.produto_de_para import ProdutoDePara
from backend.models.tenant import Tenant
from backend.models.venda import Venda
from backend.repositories.produto_de_para_repository import ProdutoDeParaRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.produto_de_para import ProdutoDeParaCreateRequest, ProdutoDeParaUpdateRequest
from backend.services.produto_de_para_service import ProdutoDeParaService


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    session = factory()
    session.add_all(
        [
            Tenant(empresa_id="11111111000101", nome="Empresa A", api_key_hash="hash-a", ativo=True),
            Tenant(empresa_id="22222222000102", nome="Empresa B", api_key_hash="hash-b", ativo=True),
        ]
    )
    session.commit()
    return session


def make_service(session: Session) -> ProdutoDeParaService:
    return ProdutoDeParaService(TenantRepository(session), ProdutoDeParaRepository(session))


def add_sale(session: Session, *, empresa_id: str, uuid: str, codigo: str, produto: str) -> None:
    session.add(
        Venda(
            uuid=uuid,
            empresa_id=empresa_id,
            codigo_produto_local=codigo,
            produto=produto,
            familia_produto="Bebidas",
            categoria_produto="Agua",
            valor=Decimal("10.00"),
            data=date(2026, 4, 16),
            data_atualizacao=datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
        )
    )
    session.commit()


def test_produto_de_para_crud_is_tenant_scoped() -> None:
    session = make_session()
    service = make_service(session)

    mapping = service.create_or_update(
        empresa_id="11111111000101",
        payload=ProdutoDeParaCreateRequest(
            codigo_produto_local="AGUA01",
            codigo_produto_web="WEB-AGUA",
            descricao_produto_local="Agua Local",
            descricao_produto_web="Agua Web",
        ),
    )
    session.commit()

    assert mapping.empresa_id == "11111111000101"
    assert mapping.cnpj == "11111111000101"
    assert mapping.codigo_produto_local == "AGUA01"

    rows_a = service.list(empresa_id="11111111000101")
    rows_b = service.list(empresa_id="22222222000102")
    assert len(rows_a) == 1
    assert rows_b == []

    updated = service.update(
        empresa_id="11111111000101",
        mapping_id=mapping.id,
        payload=ProdutoDeParaUpdateRequest(codigo_produto_web="WEB-AGUA-2", ativo=False),
    )
    session.commit()

    assert updated.codigo_produto_web == "WEB-AGUA-2"
    assert updated.ativo is False

    service.delete(empresa_id="11111111000101", mapping_id=mapping.id)
    session.commit()

    assert session.query(ProdutoDePara).filter(ProdutoDePara.empresa_id == "11111111000101").count() == 0


def test_produto_de_para_rejects_cross_company_cnpj() -> None:
    session = make_session()
    service = make_service(session)

    with pytest.raises(HTTPException) as exc:
        service.create_or_update(
            empresa_id="11111111000101",
            payload=ProdutoDeParaCreateRequest(
                cnpj="22222222000102",
                codigo_produto_local="AGUA01",
            ),
        )

    assert exc.value.status_code == 400


def test_produtos_sem_de_para_excludes_mapped_and_other_tenants() -> None:
    session = make_session()
    service = make_service(session)
    add_sale(session, empresa_id="11111111000101", uuid="sale-a", codigo="AGUA01", produto="Agua")
    add_sale(session, empresa_id="11111111000101", uuid="sale-b", codigo="LANCHE01", produto="Lanche")
    add_sale(session, empresa_id="22222222000102", uuid="sale-c", codigo="AGUA01", produto="Agua Empresa B")

    service.create_or_update(
        empresa_id="11111111000101",
        payload=ProdutoDeParaCreateRequest(
            codigo_produto_local="AGUA01",
            codigo_produto_web="WEB-AGUA",
        ),
    )
    session.commit()

    unmapped_a = service.list_unmapped_products(empresa_id="11111111000101")
    unmapped_b = service.list_unmapped_products(empresa_id="22222222000102")

    assert [item["codigo_produto_local"] for item in unmapped_a] == ["LANCHE01"]
    assert [item["codigo_produto_local"] for item in unmapped_b] == ["AGUA01"]
