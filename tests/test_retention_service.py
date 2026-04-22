from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base
from backend.models.tenant import Tenant
from backend.models.venda import Venda, VendaHistorico
from backend.services.retention_service import RetentionService


def _make_session_factory() -> sessionmaker:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _seed_tenant(session: Session, empresa_id: str, nome: str) -> None:
    session.add(
        Tenant(
            empresa_id=empresa_id,
            nome=nome,
            api_key_hash=f"hash-{empresa_id}",
            ativo=True,
        )
    )


def _seed_sale(
    session: Session,
    *,
    empresa_id: str,
    uuid: str,
    sale_date: date,
    produto: str,
) -> None:
    session.add(
        Venda(
            uuid=uuid,
            empresa_id=empresa_id,
            branch_code="BR-01",
            terminal_code="TR-01",
            produto=produto,
            valor=Decimal("10.00"),
            data=sale_date,
            data_atualizacao=datetime.combine(sale_date, datetime.min.time(), tzinfo=UTC),
        )
    )


def test_retention_service_archive_mode_respects_14_month_boundary() -> None:
    session_factory = _make_session_factory()
    cutoff_date = (datetime.now(UTC) - relativedelta(months=14)).date()
    old_date = cutoff_date - relativedelta(days=1)
    boundary_date = cutoff_date
    recent_date = cutoff_date + relativedelta(days=1)

    with session_factory() as session:
        _seed_tenant(session, "11111111000101", "Empresa A")
        _seed_tenant(session, "22222222000101", "Empresa B")
        _seed_sale(
            session,
            empresa_id="11111111000101",
            uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            sale_date=old_date,
            produto="Produto Antigo A",
        )
        _seed_sale(
            session,
            empresa_id="11111111000101",
            uuid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            sale_date=boundary_date,
            produto="Produto Limite A",
        )
        _seed_sale(
            session,
            empresa_id="22222222000101",
            uuid="cccccccc-cccc-cccc-cccc-cccccccccccc",
            sale_date=old_date,
            produto="Produto Antigo B",
        )
        _seed_sale(
            session,
            empresa_id="22222222000101",
            uuid="dddddddd-dddd-dddd-dddd-dddddddddddd",
            sale_date=recent_date,
            produto="Produto Recente B",
        )
        session.commit()

    service = RetentionService(
        session_factory=session_factory,
        retention_months=14,
        retention_mode="archive",
    )

    processed = service.run()

    assert processed == 2

    with session_factory() as session:
        remaining = session.query(Venda).order_by(Venda.uuid).all()
        archived = session.query(VendaHistorico).order_by(VendaHistorico.uuid).all()

    assert [item.uuid for item in remaining] == [
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "dddddddd-dddd-dddd-dddd-dddddddddddd",
    ]
    assert [item.empresa_id for item in remaining] == [
        "11111111000101",
        "22222222000101",
    ]
    assert [item.uuid for item in archived] == [
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "cccccccc-cccc-cccc-cccc-cccccccccccc",
    ]
    assert [item.empresa_id for item in archived] == [
        "11111111000101",
        "22222222000101",
    ]


def test_retention_service_delete_mode_removes_old_rows_without_archiving() -> None:
    session_factory = _make_session_factory()
    cutoff_date = (datetime.now(UTC) - relativedelta(months=14)).date()
    old_date = cutoff_date - relativedelta(days=5)
    recent_date = cutoff_date + relativedelta(days=10)

    with session_factory() as session:
        _seed_tenant(session, "33333333000101", "Empresa C")
        _seed_sale(
            session,
            empresa_id="33333333000101",
            uuid="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            sale_date=old_date,
            produto="Produto Antigo C",
        )
        _seed_sale(
            session,
            empresa_id="33333333000101",
            uuid="ffffffff-ffff-ffff-ffff-ffffffffffff",
            sale_date=recent_date,
            produto="Produto Recente C",
        )
        session.commit()

    service = RetentionService(
        session_factory=session_factory,
        retention_months=14,
        retention_mode="delete",
    )

    processed = service.run()

    assert processed == 1

    with session_factory() as session:
        remaining = session.query(Venda).order_by(Venda.uuid).all()
        archived_count = session.query(VendaHistorico).count()

    assert [item.uuid for item in remaining] == [
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    ]
    assert archived_count == 0
