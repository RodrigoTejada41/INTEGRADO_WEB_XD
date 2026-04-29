from datetime import date, datetime
from pathlib import Path

from agent_local.db.xd_sales_mapper import build_xd_salesdocuments_query, canonicalize_sales_row
from agent_local.sync.checkpoint_store import CheckpointStore
from agent_local.sync.sync_runner import SyncRunner


def test_canonicalize_sales_row_preserves_report_dimensions() -> None:
    row = {
        "uuid": "sale-1",
        "empresa_id": "12345678000199",
        "produto": "Produto A",
        "valor": "99.90",
        "data": date(2026, 4, 28),
        "data_atualizacao": datetime(2026, 4, 28, 10, 30),
        "branch_code": "0001",
        "terminal_code": "PDV-01",
        "tipo_venda": "Fatura",
        "forma_pagamento": "PIX",
        "familia_produto": "Bebidas",
    }

    result = canonicalize_sales_row(row)

    assert result["data_atualizacao"] == "2026-04-28T10:30:00+00:00"
    assert result["branch_code"] == "0001"
    assert result["terminal_code"] == "PDV-01"
    assert result["tipo_venda"] == "Fatura"
    assert result["forma_pagamento"] == "PIX"
    assert result["familia_produto"] == "Bebidas"


def test_build_xd_salesdocuments_query_adds_family_and_payment_mapping() -> None:
    columns = {
        "DocumentKeyId",
        "ItemKeyId",
        "CloseDate",
        "CreationDate",
        "ItemDescription",
        "TotalAmount",
        "Terminal",
        "DocumentDescription",
        "ItemGroupId",
        "Number",
        "SerieId",
    }
    tables = {"salesdocumentsreportview", "itemsgroups", "invoicepaymentdetails", "xconfigpaymenttypes"}

    query = build_xd_salesdocuments_query(columns=columns, tables=tables)

    assert ":empresa_id AS empresa_id" in query
    assert "v.Terminal AS terminal_code" in query
    assert "v.DocumentDescription AS tipo_venda" in query
    assert "itemsgroups ig" in query
    assert "xconfigpaymenttypes xpt" in query
    assert "AS forma_pagamento" in query


def test_build_xd_salesdocuments_query_maps_family_through_items_table() -> None:
    columns = {
        "DocumentKeyId",
        "ItemKeyId",
        "CloseDate",
        "CreationDate",
        "ItemDescription",
        "TotalAmount",
    }
    tables = {"salesdocumentsreportview", "Items", "Itemsgroups"}
    table_columns = {
        "salesdocumentsreportview": columns,
        "Items": {"KeyId", "GroupId"},
        "Itemsgroups": {"Id", "Description"},
    }

    query = build_xd_salesdocuments_query(columns=columns, tables=tables, table_columns=table_columns)

    assert "FROM items i" in query
    assert "INNER JOIN itemsgroups ig" in query
    assert "ig.`Id` = i.`GroupId`" in query
    assert "i.`KeyId` = v.ItemKeyId" in query
    assert "AS familia_produto" in query


class FakeMariaDBClient:
    def fetch_changed_vendas(self, empresa_id: str, since: datetime, limit: int) -> list[dict]:
        return [
            {
                "uuid": "sale-1",
                "empresa_id": empresa_id,
                "produto": "Produto A",
                "valor": "99.90",
                "data": "2026-04-28",
                "data_atualizacao": "2026-04-28T10:30:00+00:00",
                "branch_code": "0001",
                "terminal_code": "PDV-01",
                "tipo_venda": "Fatura",
                "forma_pagamento": "PIX",
                "familia_produto": "Bebidas",
            }
        ]

    def fetch_source_metadata(self, empresa_id: str) -> dict[str, object]:
        return {
            "cnpj": empresa_id,
            "company_name": "Empresa Teste",
            "payment_methods": ["PIX", "Dinheiro"],
        }


class FakeSyncApiClient:
    def __init__(self) -> None:
        self.payload: dict | None = None

    def send_sync_batch(self, payload: dict, api_key: str | None = None) -> dict:
        self.payload = payload
        return {"status": "ok", "processed_count": len(payload["records"])}


def test_sync_runner_sends_report_dimensions_to_web_api() -> None:
    api_client = FakeSyncApiClient()
    checkpoint = CheckpointStore("output/test_agent_local_sales_mapping/checkpoints.json")
    Path("output/test_agent_local_sales_mapping/checkpoints.json").unlink(missing_ok=True)
    runner = SyncRunner(
        empresa_id="12345678000199",
        mariadb_client=FakeMariaDBClient(),
        api_client=api_client,
        checkpoint_store=checkpoint,
        batch_size=500,
        api_key_provider=lambda: "local-key",
    )

    response = runner.run_once()

    assert response["processed_count"] == 1
    assert api_client.payload is not None
    assert api_client.payload["source_metadata"]["cnpj"] == "12345678000199"
    assert api_client.payload["source_metadata"]["company_name"] == "Empresa Teste"
    assert api_client.payload["source_metadata"]["payment_methods"] == ["PIX", "Dinheiro"]
    record = api_client.payload["records"][0]
    assert record["branch_code"] == "0001"
    assert record["terminal_code"] == "PDV-01"
    assert record["tipo_venda"] == "Fatura"
    assert record["forma_pagamento"] == "PIX"
    assert record["familia_produto"] == "Bebidas"
