from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _reload_local_api():
    for name in list(sys.modules):
        if name == "agent_local.local_api" or name.startswith("agent_local.orders"):
            sys.modules.pop(name, None)
    return importlib.import_module("agent_local.local_api")


def _order_headers(client: TestClient, db_path: Path, token: str = "local-token-test") -> dict[str, str]:
    from agent_local.orders.repository import hash_order_password

    headers = {"X-Local-Token": token}
    assert client.get("/orders/users", headers=headers).status_code == 200
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO local_order_operators (code, name, password_hash, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                password_hash = excluded.password_hash,
                active = 1
            """,
            ("OP01", "Ana Caixa", hash_order_password("1234")),
        )
        connection.commit()
    login = client.post(
        "/orders/login",
        headers=headers,
        json={"operator_code": "OP01", "password": "1234"},
    )
    assert login.status_code == 200, login.text
    headers["X-Order-Session"] = login.json()["session_token"]
    return headers


def test_order_catalog_prefers_real_retail_price_columns() -> None:
    from agent_local.db.mariadb_client import MariaDBClient

    db_path = Path("output/test_agent_local_orders/catalog_prices.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE items (
                    KeyId TEXT NOT NULL,
                    Description TEXT NOT NULL,
                    GroupId TEXT NULL,
                    RetailPrice1 NUMERIC NULL,
                    AskingPrice NUMERIC NULL,
                    Inactive INTEGER NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE itemsgroups (
                    Id TEXT NOT NULL,
                    Description TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(text("INSERT INTO itemsgroups VALUES ('G1', 'BEBIDAS')"))
        connection.execute(
            text(
                """
                INSERT INTO items (
                    KeyId, Description, GroupId, RetailPrice1, AskingPrice, Inactive
                )
                VALUES ('AGUA', 'Agua', 'G1', 6.50, 0, 0)
                """
            )
        )

    client = MariaDBClient("sqlite://")
    client.session_factory = sessionmaker(bind=engine, class_=Session, autoflush=False)
    client._list_columns = lambda session, table_name: {  # type: ignore[method-assign]
        "items": {"KeyId", "Description", "GroupId", "RetailPrice1", "AskingPrice", "Inactive"},
        "itemsgroups": {"Id", "Description"},
    }[table_name]
    with client.session_factory() as session:
        catalog = {
            "products": client._discover_order_products(
                session,
                {"items", "itemsgroups"},
                {
                    "items": {"KeyId", "Description", "GroupId", "RetailPrice1", "AskingPrice", "Inactive"},
                    "itemsgroups": {"Id", "Description"},
                },
            )
        }

    assert catalog["products"] == [
        {
            "product_code": "AGUA",
            "description": "Agua",
            "family": "BEBIDAS",
            "unit_price": "6.5",
        }
    ]


def test_local_order_api_creates_order_offline_and_calculates_total() -> None:
    db_path = Path("output/test_agent_local_orders/orders.db")
    token_file = Path("output/test_agent_local_orders/local_api_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        unauthorized = client.post(
            "/orders",
            json={
                "customer_name": "Cliente Teste",
                "items": [
                    {"product_code": "P001", "description": "Produto 1", "quantity": "2", "unit_price": "10.50"}
                ],
            },
        )
        assert unauthorized.status_code == 401

        created = client.post(
            "/orders",
            headers=headers,
            json={
                "customer_name": "Cliente Teste",
                "notes": "Retirar no balcao",
                "items": [
                    {"product_code": "P001", "description": "Produto 1", "quantity": "2", "unit_price": "10.50"},
                    {"product_code": "P002", "description": "Produto 2", "quantity": "1", "unit_price": "5.00"},
                ],
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["empresa_id"] == "12345678000199"
        assert body["status"] == "draft"
        assert body["sync_status"] == "pending"
        assert body["total_amount"] == "26.00"
        assert len(body["items"]) == 2

        listed = client.get("/orders", headers=headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] == 1
        assert listed.json()["orders"][0]["uuid"] == body["uuid"]


def test_local_orders_web_ui_is_available() -> None:
    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        response = client.get("/orders/ui")

    assert response.status_code == 200
    assert "Comandas Locais" in response.text
    assert "API local separada do sync de relatorios" in response.text
    assert "Entrar" in response.text
    assert "Pedido" in response.text
    assert "Consultar comanda" in response.text
    assert "Imprimir pre-conta" in response.text
    assert "Buscar produto" in response.text
    assert "Revisar pedido" in response.text
    assert "Confirmar pedido" in response.text
    assert "Lixeira" in response.text
    assert "CONTROLE POR VOZ" in response.text
    assert "CAIXA DE SAIDA" in response.text
    assert "MENSAGENS" in response.text
    assert "ANULAR" in response.text
    assert "SUBTOTAL" in response.text
    assert "TRANSFERENCIA" in response.text
    assert "PAGAMENTO PARCIAL" in response.text
    assert "DESCONTO" in response.text


def test_local_comandas_use_operator_catalog_item_notes_and_prebill() -> None:
    db_path = Path("output/test_agent_local_orders/comandas.db")
    token_file = Path("output/test_agent_local_orders/comandas_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        assert client.get("/orders/operators", headers=headers).status_code == 200

        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO local_order_products (
                    product_code, description, family, unit_price, active
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                ("BUR01", "Burger Classico", "Lanches", "25.00", 1),
            )
            connection.commit()

        operators = client.get("/orders/operators", headers=headers)
        assert operators.status_code == 200, operators.text
        assert operators.json()["operators"] == [{"code": "OP01", "name": "Ana Caixa"}]

        families = client.get("/orders/product-families", headers=headers)
        assert families.status_code == 200, families.text
        assert families.json()["families"] == ["Lanches"]

        products = client.get("/orders/products?family=Lanches", headers=headers)
        assert products.status_code == 200, products.text
        assert products.json()["products"][0]["product_code"] == "BUR01"

        found = client.get("/orders/products?q=BUR01", headers=headers)
        assert found.status_code == 200, found.text
        assert found.json()["products"][0]["description"] == "Burger Classico"

        first = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "001",
                "table_reference": "10",
                "operator_code": "OP01",
                "items": [
                    {
                        "product_code": "BUR01",
                        "description": "Burger Classico",
                        "quantity": "2",
                        "unit_price": "25.00",
                        "notes": "sem cebola",
                    }
                ],
            },
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "002",
                "table_reference": "10",
                "operator_code": "OP01",
                "items": [
                    {
                        "product_code": "BUR01",
                        "description": "Burger Classico",
                        "quantity": "1",
                        "unit_price": "25.00",
                    }
                ],
            },
        )
        assert second.status_code == 201, second.text

        first_body = first.json()
        second_body = second.json()
        assert first_body["table_reference"] == second_body["table_reference"] == "10"
        assert first_body["command_number"] == "001"
        assert second_body["command_number"] == "002"
        assert first_body["operator_name"] == "Ana Caixa"
        assert first_body["items"][0]["notes"] == "sem cebola"
        assert first_body["total_amount"] == "50.00"

        listed = client.get("/orders?table_reference=10", headers=headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["total"] == 2

        prebill = client.get(f"/orders/{first_body['uuid']}/prebill", headers=headers)
        assert prebill.status_code == 200, prebill.text
        assert "Comanda 001" in prebill.text
        assert "Mesa 10" in prebill.text
        assert "Ana Caixa" in prebill.text
        assert "sem cebola" in prebill.text


def test_local_comanda_can_be_edited_cancelled_and_closed() -> None:
    db_path = Path("output/test_agent_local_orders/operations.db")
    token_file = Path("output/test_agent_local_orders/operations_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        created = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "010",
                "table_reference": "5",
                "items": [
                    {
                        "product_code": "AGUA",
                        "description": "Agua",
                        "quantity": "1",
                        "unit_price": "5.00",
                    }
                ],
            },
        )
        assert created.status_code == 201, created.text
        order_uuid = created.json()["uuid"]
        first_item_id = created.json()["items"][0]["id"]

        added = client.post(
            f"/orders/{order_uuid}/items",
            headers=headers,
            json={
                "product_code": "LAN01",
                "description": "Lanche",
                "quantity": "2",
                "unit_price": "20.00",
                "notes": "ponto da carne",
            },
        )
        assert added.status_code == 200, added.text
        assert added.json()["total_amount"] == "45.00"
        added_item_id = [item["id"] for item in added.json()["items"] if item["product_code"] == "LAN01"][0]

        duplicated = client.post(
            f"/orders/{order_uuid}/items",
            headers=headers,
            json={
                "product_code": "LAN01",
                "description": "Lanche",
                "quantity": "1",
                "unit_price": "20.00",
                "notes": "ponto da carne",
            },
        )
        assert duplicated.status_code == 200, duplicated.text
        assert duplicated.json()["total_amount"] == "65.00"
        assert len([item for item in duplicated.json()["items"] if item["product_code"] == "LAN01"]) == 1

        updated = client.patch(
            f"/orders/{order_uuid}/items/{added_item_id}",
            headers=headers,
            json={"quantity": "3", "notes": "sem cebola"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["total_amount"] == "65.00"
        assert [item for item in updated.json()["items"] if item["id"] == added_item_id][0]["notes"] == "sem cebola"

        removed = client.delete(f"/orders/{order_uuid}/items/{first_item_id}", headers=headers)
        assert removed.status_code == 200, removed.text
        assert removed.json()["total_amount"] == "60.00"
        assert len(removed.json()["items"]) == 1

        cleared_order = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "012",
                "table_reference": "5",
                "items": [
                    {"product_code": "AGUA", "description": "Agua", "quantity": "1", "unit_price": "5.00"}
                ],
            },
        )
        clear_uuid = cleared_order.json()["uuid"]
        cleared = client.delete(f"/orders/{clear_uuid}/items", headers=headers)
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["items"] == []
        assert cleared.json()["total_amount"] == "0.00"

        closed = client.post(
            f"/orders/{order_uuid}/close",
            headers=headers,
            json={"payment_method": "dinheiro", "amount_paid": "60.00"},
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == "closed"
        assert closed.json()["payment_method"] == "dinheiro"

        blocked = client.post(
            f"/orders/{order_uuid}/items",
            headers=headers,
            json={
                "product_code": "REF01",
                "description": "Refrigerante",
                "quantity": "1",
                "unit_price": "8.00",
            },
        )
        assert blocked.status_code == 409

        cancel_created = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "011",
                "table_reference": "5",
                "items": [
                    {
                        "product_code": "CAFE",
                        "description": "Cafe",
                        "quantity": "1",
                        "unit_price": "4.00",
                    }
                ],
            },
        )
        cancel_uuid = cancel_created.json()["uuid"]
        canceled = client.post(f"/orders/{cancel_uuid}/cancel", headers=headers, json={"reason": "cliente desistiu"})
        assert canceled.status_code == 200, canceled.text
        assert canceled.json()["status"] == "cancelled"


def test_local_comanda_main_menu_operations_log_critical_actions() -> None:
    db_path = Path("output/test_agent_local_orders/menu_operations.db")
    token_file = Path("output/test_agent_local_orders/menu_operations_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        created = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "050",
                "people_count": 3,
                "table_reference": "15",
                "items": [
                    {"product_code": "AGUA", "description": "Agua", "quantity": "2", "unit_price": "8.00"},
                    {"product_code": "LAN01", "description": "Lanche", "quantity": "1", "unit_price": "20.00"},
                ],
            },
        )
        assert created.status_code == 201, created.text
        order_uuid = created.json()["uuid"]

        me = client.get("/orders/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json()["operator"]["code"] == "OP01"
        assert me.json()["permissions"]["order.discount"] is True

        subtotal = client.get("/orders/subtotal?command_number=050", headers=headers)
        assert subtotal.status_code == 200, subtotal.text
        assert subtotal.json()["payload"]["subtotal"] == "36.00"

        discount = client.post(
            "/orders/discount",
            headers=headers,
            json={"command_number": "050", "discount_type": "fixed", "value": "6.00", "reason": "cortesia"},
        )
        assert discount.status_code == 200, discount.text
        assert discount.json()["payload"]["discounts"] == "6.00"
        assert discount.json()["payload"]["remaining"] == "30.00"

        partial = client.post(
            "/orders/partial-payment",
            headers=headers,
            json={"command_number": "050", "payment_method": "pix", "amount": "10.00"},
        )
        assert partial.status_code == 200, partial.text
        assert partial.json()["payload"]["partial_payments"] == "10.00"
        assert partial.json()["payload"]["remaining"] == "20.00"

        transfer = client.post(
            "/orders/transfer",
            headers=headers,
            json={
                "transfer_type": "table",
                "source_order_uuid": order_uuid,
                "destination_table_reference": "16",
                "reason": "cliente mudou de mesa",
            },
        )
        assert transfer.status_code == 200, transfer.text
        assert transfer.json()["order"]["table_reference"] == "16"

        voice = client.post("/orders/voice-command", headers=headers)
        assert voice.status_code == 200, voice.text
        assert voice.json()["status"] == "planned"

        messages = client.get("/orders/messages", headers=headers)
        assert messages.status_code == 200, messages.text
        assert messages.json()["messages"] == []

        outbox = client.get("/orders/outbox", headers=headers)
        assert outbox.status_code == 200, outbox.text
        assert any(event["event_type"] == "order.created" for event in outbox.json()["events"])

        with sqlite3.connect(db_path) as connection:
            logs = connection.execute(
                "SELECT operation_type FROM local_order_operation_logs ORDER BY id"
            ).fetchall()
        assert [row[0] for row in logs] == ["discount", "partial_payment", "transfer"]


def test_local_comanda_supports_split_payments_in_prebill() -> None:
    db_path = Path("output/test_agent_local_orders/split_payments.db")
    token_file = Path("output/test_agent_local_orders/split_payments_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        created = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "020",
                "table_reference": "6",
                "items": [
                    {
                        "product_code": "SUSHI",
                        "description": "Combo Sushi",
                        "quantity": "1",
                        "unit_price": "70.00",
                    }
                ],
            },
        )
        order_uuid = created.json()["uuid"]

        insufficient = client.post(
            f"/orders/{order_uuid}/close",
            headers=headers,
            json={
                "payments": [
                    {"payment_method": "dinheiro", "amount": "30.00"},
                    {"payment_method": "pix", "amount": "20.00"},
                ]
            },
        )
        assert insufficient.status_code == 400

        closed = client.post(
            f"/orders/{order_uuid}/close",
            headers=headers,
            json={
                "payments": [
                    {"payment_method": "dinheiro", "amount": "30.00"},
                    {"payment_method": "pix", "amount": "40.00"},
                ]
            },
        )
        assert closed.status_code == 200, closed.text
        body = closed.json()
        assert body["status"] == "closed"
        assert body["amount_paid"] == "70.00"
        assert body["payment_method"] == "dinheiro + pix"
        assert body["payments"] == [
            {"payment_method": "dinheiro", "amount": "30.00"},
            {"payment_method": "pix", "amount": "40.00"},
        ]

        prebill = client.get(f"/orders/{order_uuid}/prebill", headers=headers)
        assert prebill.status_code == 200, prebill.text
        assert "dinheiro" in prebill.text
        assert "pix" in prebill.text
        assert "40.00" in prebill.text


def test_local_comanda_generates_thermal_receipt_and_print_job() -> None:
    db_path = Path("output/test_agent_local_orders/thermal_receipt.db")
    token_file = Path("output/test_agent_local_orders/thermal_receipt_token.txt")
    jobs_dir = Path("output/test_agent_local_orders/print_jobs")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"
    os.environ["LOCAL_ORDER_PRINT_JOBS_DIR"] = str(jobs_dir)
    os.environ["LOCAL_ORDER_RECEIPT_WIDTH"] = "32"
    os.environ.pop("LOCAL_ORDER_PRINTER_NAME", None)

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        created = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "030",
                "table_reference": "9",
                "operator_name": "Caixa",
                "items": [
                    {
                        "product_code": "PIZZA",
                        "description": "Pizza Grande",
                        "quantity": "1",
                        "unit_price": "80.00",
                        "notes": "meia mussarela",
                    }
                ],
            },
        )
        assert created.status_code == 201, created.text
        order_uuid = created.json()["uuid"]

        receipt = client.get(f"/orders/{order_uuid}/thermal-receipt", headers=headers)
        assert receipt.status_code == 200, receipt.text
        assert "PRE-CONTA" in receipt.text
        assert "COMANDA 030" in receipt.text
        assert "Pizza Grande" in receipt.text
        assert "TOTAL" in receipt.text
        assert "80.00" in receipt.text

        printed = client.post(f"/orders/{order_uuid}/print", headers=headers)
        assert printed.status_code == 200, printed.text
        body = printed.json()
        assert body["status"] == "queued"
        assert body["printer_name"] is None
        assert body["message"] == "LOCAL_ORDER_PRINTER_NAME nao configurado."
        job_path = Path(body["job_path"])
        assert job_path.exists()
        assert "COMANDA 030" in job_path.read_text(encoding="utf-8")
