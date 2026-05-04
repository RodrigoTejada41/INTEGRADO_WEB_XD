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


def test_order_catalog_imports_operator_password_for_local_login() -> None:
    from agent_local.db.mariadb_client import MariaDBClient
    from agent_local.orders.repository import LocalOrderRepository

    db_path = Path("output/test_agent_local_orders/catalog_operator_password.db")
    local_db_path = Path("output/test_agent_local_orders/catalog_operator_password_local.db")
    for path in (db_path, local_db_path):
        if path.exists():
            path.unlink()

    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}", future=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE xconfigoperators (
                    Code TEXT NOT NULL,
                    Name TEXT NOT NULL,
                    Password TEXT NOT NULL,
                    Inactive INTEGER NULL
                )
                """
            )
        )
        connection.execute(text("INSERT INTO xconfigoperators VALUES ('ADM', 'ADM', '1234', 0)"))

    client = MariaDBClient("sqlite://")
    client.session_factory = sessionmaker(bind=engine, class_=Session, autoflush=False)
    client._list_columns = lambda session, table_name: {  # type: ignore[method-assign]
        "Code",
        "Name",
        "Password",
        "Inactive",
    }

    with client.session_factory() as session:
        operators = client._discover_order_operators(session, {"xconfigoperators"})

    repository = LocalOrderRepository(local_db_path)
    repository.upsert_catalog(operators=operators, products=[])

    session = repository.authenticate_operator("ADM", "1234")
    assert session.operator_code == "ADM"
    assert repository.authenticate_operator("ADM", "1234").operator_name == "ADM"


def test_order_catalog_accepts_xd_sha256_operator_password() -> None:
    from agent_local.orders.repository import LocalOrderRepository

    db_path = Path("output/test_agent_local_orders/xd_sha256_password.db")
    if db_path.exists():
        db_path.unlink()

    repository = LocalOrderRepository(db_path)
    repository.upsert_catalog(
        operators=[
            {
                "code": "ADM",
                "name": "ADM",
                "password": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4",
            }
        ],
        products=[],
    )

    session = repository.authenticate_operator("ADM", "1234")
    assert session.operator_code == "ADM"


def test_local_login_learns_imported_operator_password_on_server() -> None:
    db_path = Path("output/test_agent_local_orders/login_learns_password.db")
    token_file = Path("output/test_agent_local_orders/login_learns_password_token.txt")
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
        headers = {"X-Local-Token": "local-token-test"}
        repository = local_api._order_repository()
        repository.upsert_catalog(
            operators=[{"code": "ADM", "name": "ADM", "password": "external-xd-hash"}],
            products=[],
        )

        login = client.post("/orders/login", headers=headers, json={"operator_code": "ADM", "password": "4321"})
        assert login.status_code == 200, login.text

        second_login = client.post("/orders/login", headers=headers, json={"operator_code": "ADM", "password": "4321"})
        assert second_login.status_code == 200, second_login.text


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

        mesa_only = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "99",
                "items": [
                    {"product_code": "P003", "description": "Produto 3", "quantity": "1", "unit_price": "3.00"}
                ],
            },
        )
        assert mesa_only.status_code == 201, mesa_only.text
        assert mesa_only.json()["command_number"] == "99"
        assert mesa_only.json()["table_reference"] is None


def test_local_orders_web_ui_is_available() -> None:
    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        response = client.get("/orders/ui")

    assert response.status_code == 200
    assert "Movi_commanda" in response.text
    assert "Versao 1.0.0" in response.text
    assert "USUARIOS" in response.text
    assert "DEFINICOES" in response.text
    assert "INICIAR" in response.text
    assert "Entrar" in response.text
    assert "Definicoes" in response.text
    assert "Smart Connect" in response.text
    assert "Impressora Bluetooth" in response.text
    assert "Sobre a aplicacao" in response.text
    assert "Buscar produto" in response.text
    assert "Revisar pedido" in response.text
    assert "Confirmar pedido" in response.text
    assert "Mesa identifica o pedido. Referencia e apenas apoio operacional." in response.text
    assert "<th>Mesa</th><th>Referencia</th>" in response.text
    assert "Numero da comanda" not in response.text
    assert "Lixeira" in response.text
    assert "CONTROLE POR VOZ" in response.text
    assert "CAIXA DE SAIDA" in response.text
    assert "MENSAGENS" in response.text
    assert "ANULAR" in response.text
    assert "SUBTOTAL" in response.text
    assert "TRANSFERENCIA" in response.text
    assert "PAGAMENTO PARCIAL" in response.text
    assert "DESCONTO" in response.text
    assert "FECHAR CONTA" in response.text
    assert "Nao tem permissao para fechar conta." in response.text
    assert "order.close" in response.text
    assert "/orders/local-token" in response.text
    assert "Token local invalido" in response.text
    assert "localFetch(url, options = {}, retried = false)" in response.text
    assert "loadLocalTokenIfAvailable(true)" in response.text
    assert "requireTechnicalSession()" in response.text
    assert "Entre em USUARIOS com operador tecnico" in response.text
    assert "if (!(await requireTechnicalSession())) return;" in response.text
    assert "XD" not in response.text
    assert "XD Orders" not in response.text
    assert "XDOrders" not in response.text


def test_client_installer_removes_old_movisync_residue() -> None:
    installer = Path("infra/client-agent/install-agent-client.ps1").read_text(encoding="utf-8")
    quick_start = Path("infra/client-agent/COMECE_AQUI.bat").read_text(encoding="utf-8")
    readme = Path("infra/client-agent/README.md").read_text(encoding="utf-8")
    requirements = Path("requirements.txt").read_text(encoding="utf-8")

    assert '[string]$InstallDir = "C:\\Movi_commanda"' in installer
    assert '$LegacyInstallDirs = @("C:\\MoviSyncAgent")' in installer
    assert "Backup-InstallState" in installer
    assert "Restore-InstallState" in installer
    assert "Remove-InstallTree" in installer
    assert "Remove-DesktopShortcutsByTargetRoots" in installer
    assert "Invoke-CheckedCommand" in installer
    assert "import fastapi, uvicorn, pydantic, pystray, PIL" in installer
    assert '$LocalApiPort = "8765"' in installer
    assert "Ensure-LocalApiFirewallRule" in installer
    assert "ACESSO_REDE_LOCAL.txt" in installer
    assert "--host 0.0.0.0 --port $LocalApiPort" in installer
    assert "Iniciar_Relatorios_Sync.cmd" in installer
    assert "Abrir_Status_Relatorios.cmd" in installer
    assert "Abrir_Icone_API.vbs" in installer
    assert "agent_local.api_tray" in installer
    assert "Definir_Senha_Operador_Local.cmd" in installer
    assert "Abrir_Status_Sync.vbs" not in installer
    assert "Iniciar_Agente.vbs" not in installer
    assert "Iniciar_Movi_commanda_Windows.vbs" in installer
    assert "Movi_commanda API Local -" not in installer
    assert "Movi_commanda Status -" not in installer
    assert "Movi_commanda Iniciar Servico -" not in installer
    assert "MoviSync" not in quick_start
    assert "C:\\MoviSyncAgent" not in readme
    assert Path("infra/client-agent/scripts/set-local-operator-password.ps1").exists()
    assert "psycopg2-binary==2.9.10" in requirements
    assert "psycopg2-binary==2.9.9" not in requirements


def test_local_command_network_mode_uses_lan_api_and_sqlite_cache_controls() -> None:
    autostart = Path("agent_local/windows_autostart.py").read_text(encoding="utf-8")
    repository = Path("agent_local/orders/repository.py").read_text(encoding="utf-8")
    api_tray = Path("agent_local/api_tray.py").read_text(encoding="utf-8")

    assert 'DEFAULT_LOCAL_API_HOST = "0.0.0.0"' in autostart
    assert "windows-autostart.lock" in autostart
    assert 'os.getenv("LOCAL_API_HOST", DEFAULT_LOCAL_API_HOST)' in autostart
    assert '"--host", host, "--port", port' in autostart
    assert "agent_local.main" not in autostart
    assert "agent_local.tray_app" not in autostart
    assert "agent_local.api_tray" in autostart
    assert "start_api_tray()" in autostart
    assert "/orders/technical/status" in api_tray
    assert "IP servidor:" in api_tray
    assert "Clientes web conectados:" in api_tray
    assert "Ver clientes conectados" in api_tray
    assert "sqlite3.connect(self.db_path, timeout=30)" in repository
    assert "PRAGMA busy_timeout = 30000" in repository
    assert "PRAGMA journal_mode = WAL" in repository
    assert "PRAGMA synchronous = NORMAL" in repository


def test_local_commanda_technical_network_and_database_endpoints_do_not_expose_password() -> None:
    db_path = Path("output/test_agent_local_orders/technical.db")
    token_file = Path("output/test_agent_local_orders/technical_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"
    os.environ["LOCAL_API_HOST"] = "0.0.0.0"
    os.environ["LOCAL_API_PORT"] = "8765"
    os.environ["AGENT_MARIADB_URL"] = "mysql+pymysql://user:secret@127.0.0.1:3306/commanda?charset=utf8mb4"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)

        network = client.get("/orders/technical/network", headers=headers)
        assert network.status_code == 200, network.text
        assert network.json()["port"] == 8765

        database = client.get("/orders/technical/database", headers=headers)
        assert database.status_code == 200, database.text
        body = database.json()
        assert body["host"] == "127.0.0.1"
        assert body["username"] == "user"
        assert body["password_configured"] is True
        assert "secret" not in database.text

        clients = client.get("/orders/technical/clients", headers=headers)
        assert clients.status_code == 200, clients.text
        assert clients.json()["clients"]

        check = client.post("/orders/technical/check", headers=headers)
        assert check.status_code == 200, check.text
        assert check.json()["server_api"]["status"] == "connected"


def test_local_commanda_database_defaults_match_local_mariadb_standard() -> None:
    db_path = Path("output/test_agent_local_orders/database_defaults.db")
    token_file = Path("output/test_agent_local_orders/database_defaults_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"
    os.environ.pop("AGENT_MARIADB_URL", None)

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        response = client.get("/orders/technical/database", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["database_type"] == "mariadb"
    assert body["host"] == "127.0.0.1"
    assert body["port"] == 3308
    assert body["username"] == "root"
    assert body["password_configured"] is True
    assert body["ssl_enabled"] is False
    assert "root:root" not in response.text


def test_local_token_endpoint_only_returns_token_to_loopback_clients() -> None:
    db_path = Path("output/test_agent_local_orders/local_token.db")
    token_file = Path("output/test_agent_local_orders/local_token.txt")
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
        response = client.get("/orders/local-token")
        assert response.status_code == 200, response.text
        assert response.json() == {"token": "local-token-test"}


def test_local_commanda_settings_app_info_and_license() -> None:
    db_path = Path("output/test_agent_local_orders/settings.db")
    token_file = Path("output/test_agent_local_orders/settings_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"
    os.environ["LOCAL_COMMAND_APP_VERSION"] = "1.0.0"
    os.environ["LOCAL_COMMAND_VERSION_CODE"] = "100"

    local_api = _reload_local_api()

    with TestClient(local_api.app) as client:
        headers = {"X-Local-Token": "local-token-test"}

        app_info = client.get("/orders/app-info", headers=headers)
        assert app_info.status_code == 200, app_info.text
        assert app_info.json() == {
            "app_name": "Movi_commanda",
            "version_name": "1.0.0",
            "version_code": "100",
        }

        settings = client.get("/orders/settings", headers=headers)
        assert settings.status_code == 200, settings.text
        assert settings.json()["settings"]["ip_servidor"] == "127.0.0.1"

        saved = client.put(
            "/orders/settings",
            headers=headers,
            json={
                "ip_servidor": "192.168.0.10",
                "porta_servidor": 8765,
                "licenca": "LIC-TESTE",
                "ssid_wifi": "REDE-PDV",
                "impressora_bluetooth": "Printer BT",
                "dpi_impressora": 203,
                "largura_impressora": 58,
                "caracteres_por_linha": 32,
                "tema_interface": "padrao",
                "usuario_logado": "OP01",
                "versao_app": "1.0.0",
                "codigo_versao": "100",
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["settings"]["licenca"] == "LIC-TESTE"

        connection = client.post("/orders/settings/test-connection", headers=headers)
        assert connection.status_code == 200, connection.text
        assert connection.json()["host"] == "192.168.0.10"

        loaded = client.post("/orders/settings/load-server-data", headers=headers)
        assert loaded.status_code == 200, loaded.text
        assert loaded.json()["status"] == "ok"

        license_response = client.get("/orders/license", headers=headers)
        assert license_response.status_code == 200, license_response.text
        assert license_response.json()["status"] == "configured"

        validated = client.post("/orders/license/validate", headers=headers)
        assert validated.status_code == 200, validated.text
        assert validated.json()["status"] == "valid"


def test_local_commanda_status_reports_network_url_and_web_clients() -> None:
    db_path = Path("output/test_agent_local_orders/status_clients.db")
    token_file = Path("output/test_agent_local_orders/status_clients_token.txt")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"
    os.environ["LOCAL_API_PORT"] = "8765"

    local_api = _reload_local_api()
    local_api._connected_clients.clear()
    now = local_api._utc_now()
    local_api._connected_clients["127.0.0.1"] = {"ip": "127.0.0.1", "last_seen_at": now}
    local_api._connected_clients["192.168.15.25"] = {"ip": "192.168.15.25", "last_seen_at": now}

    with TestClient(local_api.app) as client:
        response = client.get("/orders/technical/status", headers={"X-Local-Token": "local-token-test"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["network"]["port"] == 8765
    assert body["clients_count"] >= 2
    assert body["web_clients_count"] == 1


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
        assert "Mesa 001" in prebill.text
        assert "Referencia 10" in prebill.text
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


def test_local_comanda_close_account_requires_permission() -> None:
    db_path = Path("output/test_agent_local_orders/close_permission.db")
    token_file = Path("output/test_agent_local_orders/close_permission_token.txt")
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
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                INSERT INTO local_order_operator_permissions (operator_code, permission, allowed)
                VALUES (?, ?, 0)
                ON CONFLICT(operator_code, permission) DO UPDATE SET allowed = excluded.allowed
                """,
                ("OP01", "order.close"),
            )
            connection.commit()

        created = client.post(
            "/orders",
            headers=headers,
            json={
                "command_number": "060",
                "items": [
                    {"product_code": "AGUA", "description": "Agua", "quantity": "1", "unit_price": "5.00"}
                ],
            },
        )
        assert created.status_code == 201, created.text
        order_uuid = created.json()["uuid"]

        me = client.get("/orders/me", headers=headers)
        assert me.status_code == 200, me.text
        assert me.json()["permissions"]["order.close"] is False

        account = client.get("/orders/account?command_number=060", headers=headers)
        assert account.status_code == 403, account.text
        assert account.json()["detail"] == "Permissao negada: order.close"

        closed = client.post(
            f"/orders/{order_uuid}/close",
            headers=headers,
            json={"payment_method": "dinheiro", "amount_paid": "5.00"},
        )
        assert closed.status_code == 403, closed.text
        assert closed.json()["detail"] == "Permissao negada: order.close"


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
        assert "MESA 030" in receipt.text
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
        assert "MESA 030" in job_path.read_text(encoding="utf-8")


def test_local_comanda_auto_prints_items_by_product_group(monkeypatch) -> None:
    db_path = Path("output/test_agent_local_orders/group_printers.db")
    token_file = Path("output/test_agent_local_orders/group_printers_token.txt")
    jobs_dir = Path("output/test_agent_local_orders/group_print_jobs")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    if jobs_dir.exists():
        for path in jobs_dir.glob("*.txt"):
            path.unlink()
    token_file.write_text("local-token-test", encoding="ascii")

    os.environ["LOCAL_ORDER_DB_PATH"] = str(db_path)
    os.environ["LOCAL_API_TOKEN_FILE"] = str(token_file)
    os.environ["AGENT_EMPRESA_ID"] = "12345678000199"
    os.environ["LOCAL_ORDER_AUTO_REFRESH_CATALOG"] = "false"
    os.environ["LOCAL_ORDER_PRINT_JOBS_DIR"] = str(jobs_dir)
    os.environ["LOCAL_ORDER_RECEIPT_WIDTH"] = "32"

    local_api = _reload_local_api()
    import agent_local.orders.printer as printer_module

    def fake_send_to_windows_printer(self, *, order_uuid, job_path):
        return printer_module.LocalPrintJob(
            order_uuid=order_uuid,
            job_path=job_path,
            status="sent",
            printer_name=self.printer_name,
        )

    monkeypatch.setattr(printer_module.LocalOrderPrinter, "_send_to_windows_printer", fake_send_to_windows_printer)

    with TestClient(local_api.app) as client:
        headers = _order_headers(client, db_path)
        local_api._order_repository().upsert_catalog(
            operators=[],
            products=[
                {"product_code": "SUSHI01", "description": "Hot Roll", "family": "Sushi", "unit_price": "30.00"},
                {"product_code": "BEB01", "description": "Agua", "family": "Bebidas", "unit_price": "5.00"},
            ],
        )
        configured = client.put(
            "/orders/technical/printers/groups",
            headers=headers,
            json={
                "printers": [
                    {"family": "Sushi", "printer_name": "Printer Sushi", "active": True},
                    {"family": "Bebidas", "printer_name": "Printer Bebidas", "active": True},
                ]
            },
        )
        assert configured.status_code == 200, configured.text

        listed = client.get("/orders/technical/printers/groups", headers=headers)
        assert listed.status_code == 200, listed.text
        assert {item["family"] for item in listed.json()["printers"]} == {"Bebidas", "Sushi"}

        created = client.post(
            "/orders/confirm",
            headers=headers,
            json={
                "command_number": "070",
                "items": [
                    {"product_code": "SUSHI01", "description": "Hot Roll", "quantity": "2", "unit_price": "30.00"},
                    {"product_code": "BEB01", "description": "Agua", "quantity": "1", "unit_price": "5.00"},
                ],
            },
        )
        assert created.status_code == 201, created.text

    jobs = sorted(jobs_dir.glob("*.txt"))
    assert len(jobs) == 2
    contents = {path.name: path.read_text(encoding="utf-8") for path in jobs}
    sushi_ticket = "\n".join(text for text in contents.values() if "SUSHI" in text)
    bebidas_ticket = "\n".join(text for text in contents.values() if "BEBIDAS" in text)
    assert "2x Hot Roll" in sushi_ticket
    assert "Agua" not in sushi_ticket
    assert "1x Agua" in bebidas_ticket
    assert "Hot Roll" not in bebidas_ticket
