from datetime import UTC, date, datetime
from decimal import Decimal

from agent_local.db.xd_sales_mapper import build_xd_salesdocuments_query, canonicalize_sales_row


def test_xd_salesdocuments_view_query_exports_report_detail_fields() -> None:
    columns = {
        "DocumentKeyId",
        "ItemKeyId",
        "CloseDate",
        "CreationDate",
        "ItemDescription",
        "TotalAmount",
        "Terminal",
        "DocumentDescription",
        "Quantity",
        "UnitPrice",
        "GrossAmount",
        "DiscountAmount",
        "Number",
        "SerieId",
        "ItemGroupId",
    }

    query = build_xd_salesdocuments_query(
        columns=columns,
        tables={"salesdocumentsreportview", "Itemsgroups", "Invoicepaymentdetails", "Xconfigpaymenttypes"},
    )

    assert "salesdocumentsreportview v" in query
    assert "v.ItemKeyId AS codigo_produto_local" in query
    assert "v.Quantity AS quantidade" in query
    assert "v.UnitPrice AS valor_unitario" in query
    assert "v.GrossAmount AS valor_bruto" in query
    assert "v.DiscountAmount AS desconto" in query
    assert "xconfigpaymenttypes" in query
    assert "itemsgroups" in query


def test_xd_documents_fallback_query_uses_reference_tables() -> None:
    query = build_xd_salesdocuments_query(
        columns=set(),
        tables={"Documentsbodys", "Documentsheaders", "Invoicepaymentdetails", "Xconfigpaymenttypes", "Itemsgroups"},
        table_columns={
            "Documentsbodys": {
                "Guid",
                "SerieId",
                "Number",
                "ItemKeyId",
                "ItemDescription",
                "CloseDate",
                "TotalAmount",
                "Quantity",
                "UnitPrice",
                "GrossAmount",
                "DiscountAmount",
                "ItemGroupId",
                "Terminal",
            },
            "Documentsheaders": {
                "SerieId",
                "Number",
                "DocumentTypeId",
                "EntityKeyId",
                "OperatorName",
                "CreationDate",
            },
            "Invoicepaymentdetails": {"InvoiceNumber", "SerieId", "PaymentTypeId"},
            "Xconfigpaymenttypes": {"Id", "Description"},
            "Itemsgroups": {"Id", "Description"},
        },
    )

    assert "FROM Documentsbodys b" in query
    assert "INNER JOIN Documentsheaders h" in query
    assert "b.ItemKeyId AS codigo_produto_local" in query
    assert "COALESCE(b.Quantity, 1) AS quantidade" in query
    assert "xconfigpaymenttypes" in query


def test_canonicalize_sales_row_preserves_local_product_code_and_financial_fields() -> None:
    row = {
        "uuid": "abc123456",
        "empresa_id": "12345678000199",
        "produto": "Produto XD",
        "codigo_produto_local": "789001",
        "quantidade": Decimal("2"),
        "valor_bruto": Decimal("20.00"),
        "desconto": Decimal("1.50"),
        "acrescimo": Decimal("0.50"),
        "valor_liquido": Decimal("19.00"),
        "valor": Decimal("19.00"),
        "cancelada": False,
        "data": date(2026, 4, 29),
        "data_atualizacao": datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
    }

    payload = canonicalize_sales_row(row)

    assert payload["codigo_produto_local"] == "789001"
    assert payload["quantidade"] == "2"
    assert payload["valor_bruto"] == "20.00"
    assert payload["valor_liquido"] == "19.00"
    assert payload["cancelada"] is False
