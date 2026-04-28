from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base
from backend.models.tenant import Tenant
from backend.models.venda import Venda
from backend.repositories.venda_repository import VendaRepository


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    session = factory()
    session.add_all(
        [
            Tenant(
                empresa_id="11111111000101",
                nome="Empresa A",
                api_key_hash="hash-a",
                ativo=True,
            ),
            Tenant(
                empresa_id="22222222000102",
                nome="Empresa B",
                api_key_hash="hash-b",
                ativo=True,
            ),
        ]
    )
    session.commit()
    return session


def test_bulk_upsert_insert() -> None:
    session = make_session()
    repository = VendaRepository(session)
    records = [
        {
            "uuid": "11111111-1111-1111-1111-111111111111",
            "branch_code": "0001",
            "terminal_code": "PDV-01",
            "tipo_venda": "presencial",
            "forma_pagamento": "cartao_credito",
            "familia_produto": "bebidas",
            "produto": "Produto A",
            "valor": Decimal("10.00"),
            "data": date(2026, 4, 16),
            "data_atualizacao": datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
        }
    ]

    inserted, updated = repository.bulk_upsert("11111111000101", records)
    session.commit()

    assert inserted == 1
    assert updated == 0
    assert session.query(Venda).count() == 1
    venda = session.query(Venda).one()
    assert venda.branch_code == "0001"
    assert venda.terminal_code == "PDV-01"
    assert venda.tipo_venda == "presencial"
    assert venda.forma_pagamento == "cartao_credito"
    assert venda.familia_produto == "bebidas"


def test_bulk_upsert_update() -> None:
    session = make_session()
    repository = VendaRepository(session)
    first = [
        {
            "uuid": "22222222-2222-2222-2222-222222222222",
            "branch_code": "0001",
            "terminal_code": "PDV-01",
            "tipo_venda": "presencial",
            "forma_pagamento": "dinheiro",
            "familia_produto": "mercearia",
            "produto": "Produto B",
            "valor": Decimal("50.00"),
            "data": date(2026, 4, 16),
            "data_atualizacao": datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
        }
    ]
    repository.bulk_upsert("11111111000101", first)
    session.commit()

    second = [
        {
            "uuid": "22222222-2222-2222-2222-222222222222",
            "branch_code": "0002",
            "terminal_code": "PDV-02",
            "tipo_venda": "delivery",
            "forma_pagamento": "pix",
            "familia_produto": "padaria",
            "produto": "Produto B - atualizado",
            "valor": Decimal("55.00"),
            "data": date(2026, 4, 16),
            "data_atualizacao": datetime(2026, 4, 16, 11, 0, tzinfo=UTC),
        }
    ]
    inserted, updated = repository.bulk_upsert("11111111000101", second)
    session.commit()

    venda = (
        session.query(Venda)
        .filter(
            Venda.empresa_id == "11111111000101",
            Venda.uuid == "22222222-2222-2222-2222-222222222222",
        )
        .one()
    )
    assert inserted == 0
    assert updated == 1
    assert venda.produto == "Produto B - atualizado"
    assert venda.branch_code == "0002"
    assert venda.terminal_code == "PDV-02"
    assert venda.tipo_venda == "delivery"
    assert venda.forma_pagamento == "pix"
    assert venda.familia_produto == "padaria"
    assert venda.valor == Decimal("55.00")


def test_bulk_upsert_tenant_isolation() -> None:
    session = make_session()
    repository = VendaRepository(session)
    same_uuid = "33333333-3333-3333-3333-333333333333"
    record_a = [
        {
            "uuid": same_uuid,
            "produto": "Produto Tenant A",
            "valor": Decimal("20.00"),
            "data": date(2026, 4, 16),
            "data_atualizacao": datetime(2026, 4, 16, 10, 0, tzinfo=UTC),
        }
    ]
    record_b = [
        {
            "uuid": same_uuid,
            "produto": "Produto Tenant B",
            "valor": Decimal("30.00"),
            "data": date(2026, 4, 16),
            "data_atualizacao": datetime(2026, 4, 16, 10, 5, tzinfo=UTC),
        }
    ]

    repository.bulk_upsert("11111111000101", record_a)
    repository.bulk_upsert("22222222000102", record_b)
    session.commit()

    count_a = session.query(Venda).filter(Venda.empresa_id == "11111111000101").count()
    count_b = session.query(Venda).filter(Venda.empresa_id == "22222222000102").count()
    assert count_a == 1
    assert count_b == 1


def test_report_breakdowns_and_time_filter() -> None:
    session = make_session()
    repository = VendaRepository(session)
    repository.bulk_upsert(
        "11111111000101",
        [
            {
                "uuid": "44444444-4444-4444-4444-444444444444",
                "tipo_venda": "presencial",
                "forma_pagamento": "pix",
                "familia_produto": "bebidas",
                "produto": "Agua",
                "valor": Decimal("10.00"),
                "data": date(2026, 4, 16),
                "data_atualizacao": datetime(2026, 4, 16, 9, 30, tzinfo=UTC),
            },
            {
                "uuid": "55555555-5555-5555-5555-555555555555",
                "tipo_venda": "delivery",
                "forma_pagamento": "cartao",
                "familia_produto": "lanches",
                "produto": "Sanduiche",
                "valor": Decimal("40.00"),
                "data": date(2026, 4, 16),
                "data_atualizacao": datetime(2026, 4, 16, 15, 30, tzinfo=UTC),
            },
        ],
    )
    session.commit()

    payment_breakdown = repository.report_sales_breakdown(
        empresa_id="11111111000101",
        group_by="forma_pagamento",
        limit=10,
        start_date=date(2026, 4, 16),
        end_date=date(2026, 4, 16),
    )
    assert {item["label"] for item in payment_breakdown} == {"pix", "cartao"}

    afternoon_overview = repository.report_overview(
        empresa_id="11111111000101",
        start_date=date(2026, 4, 16),
        end_date=date(2026, 4, 16),
        start_time=datetime(2026, 4, 16, 12, 0, tzinfo=UTC).time(),
        end_time=datetime(2026, 4, 16, 16, 0, tzinfo=UTC).time(),
    )
    assert afternoon_overview["total_records"] == 1
    assert afternoon_overview["total_sales_value"] == Decimal("40.00")

    category_overview = repository.report_overview(
        empresa_id="11111111000101",
        start_date=date(2026, 4, 16),
        end_date=date(2026, 4, 16),
        category="beb",
    )
    assert category_overview["total_records"] == 1
    assert category_overview["total_sales_value"] == Decimal("10.00")

    category_recent_sales = repository.report_recent_sales(
        empresa_id="11111111000101",
        limit=10,
        start_date=date(2026, 4, 16),
        end_date=date(2026, 4, 16),
        category="sand",
    )
    assert [sale.produto for sale in category_recent_sales] == ["Sanduiche"]
