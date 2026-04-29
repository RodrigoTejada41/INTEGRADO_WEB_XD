from datetime import UTC, date, datetime
from decimal import Decimal
import os
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(autouse=True)
def cleanup_backend_settings_cache():
    yield
    try:
        import backend.config.settings as settings_module

        settings_module.get_settings.cache_clear()
    except Exception:
        pass
    for module_name in [
        "backend.main",
        "backend.config.database",
        "backend.config.settings",
        "backend.services",
        "backend.services.admin_service",
        "backend.services.sync_service",
    ]:
        sys.modules.pop(module_name, None)


def make_session() -> Session:
    _prepare_backend_env()
    from backend.models import Base
    from backend.models.tenant import Tenant

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    session = factory()
    session.add(
        Tenant(
            empresa_id="12345678000199",
            nome="Empresa antiga",
            api_key_hash="hash-a",
            ativo=True,
        )
    )
    session.commit()
    return session


def make_payload(cnpj: str = "12345678000199"):
    _prepare_backend_env()
    from backend.schemas.sync import SyncRequest

    return SyncRequest.model_validate(
        {
            "empresa_id": "12345678000199",
            "source_metadata": {
                "cnpj": cnpj,
                "company_name": "Empresa local descoberta",
                "payment_methods": ["PIX", "Dinheiro"],
            },
            "records": [
                {
                    "uuid": "source-meta-sale-1",
                    "produto": "Produto A",
                    "valor": Decimal("10.00"),
                    "data": date(2026, 4, 28),
                    "data_atualizacao": datetime(2026, 4, 28, 10, 0, tzinfo=UTC),
                    "forma_pagamento": "PIX",
                    "familia_produto": "Bebidas",
                    "tipo_venda": "Fatura",
                }
            ],
        }
    )


def test_sync_source_metadata_updates_tenant_name_and_keeps_payment_dimension() -> None:
    _prepare_backend_env()
    from backend.repositories.tenant_repository import TenantRepository
    from backend.repositories.venda_repository import VendaRepository
    from backend.services.sync_service import SyncService

    session = make_session()
    tenant_repository = TenantRepository(session)
    service = SyncService(
        VendaRepository(session),
        tenant_repository=tenant_repository,
    )

    response = service.sync_batch("12345678000199", make_payload())
    session.commit()

    tenant = tenant_repository.get_by_empresa_id("12345678000199")
    assert response.processed_count == 1
    assert tenant is not None
    assert tenant.nome == "Empresa local descoberta"


def test_sync_source_metadata_rejects_cross_tenant_cnpj() -> None:
    _prepare_backend_env()
    from backend.repositories.tenant_repository import TenantRepository
    from backend.repositories.venda_repository import VendaRepository
    from backend.services.sync_service import SyncService

    session = make_session()
    service = SyncService(
        VendaRepository(session),
        tenant_repository=TenantRepository(session),
    )

    with pytest.raises(HTTPException) as exc:
        service.sync_batch("12345678000199", make_payload(cnpj="99999999000199"))

    assert exc.value.status_code == 403


def _prepare_backend_env() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
