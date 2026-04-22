from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base
from backend.models.tenant import Tenant
from backend.models.venda import Venda
from backend.repositories.venda_repository import VendaRepository


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    session = factory()
    session.add(
        Tenant(
            empresa_id="11111111000101",
            nome="Empresa A",
            api_key_hash="hash-a",
            ativo=True,
        )
    )
    session.commit()
    return session


def test_bulk_upsert_keeps_branch_and_terminal_scope() -> None:
    session = _session()
    repository = VendaRepository(session)
    records = [
        {
            "uuid": f"aaaaaaaa-0000-0000-0000-{index:012d}",
            "branch_code": "BR-01",
            "terminal_code": "TR-01",
            "produto": f"Produto {index}",
            "valor": Decimal("10.00"),
            "data": date(2026, 4, 16),
            "data_atualizacao": datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
        }
        for index in range(30)
    ]

    inserted, updated = repository.bulk_upsert("11111111000101", records, chunk_size=7)
    session.commit()

    assert inserted == 30
    assert updated == 0
    assert session.query(Venda).count() == 30
    first = session.query(Venda).first()
    assert first is not None
    assert first.branch_code == "BR-01"
    assert first.terminal_code == "TR-01"
