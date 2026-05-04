from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path
from html import escape
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from agent_local.config.database_config import (
    DEFAULT_DATABASE_TYPE,
    DEFAULT_MARIADB_HOST,
    DEFAULT_MARIADB_PASSWORD,
    DEFAULT_MARIADB_PORT,
    DEFAULT_MARIADB_USERNAME,
    LocalDatabaseConfig,
    LocalDatabaseConfigService,
    parse_mariadb_url,
)
from agent_local.db.mariadb_client import MariaDBClient
from agent_local.orders.printer import render_thermal_receipt
from agent_local.orders.repository import LocalOrderRepository
from agent_local.orders.schemas import (
    LocalCommandaAppInfoResponse,
    LocalCommandaSettings,
    LocalCommandaSettingsResponse,
    LocalConnectedClientListResponse,
    LocalConnectedClientView,
    LocalConnectionCheckResponse,
    LocalDatabaseConfigPayload,
    LocalDatabaseConfigResponse,
    LocalNetworkAddressView,
    LocalNetworkInfoResponse,
    LocalOperatorListResponse,
    LocalOperatorContextResponse,
    LocalOperatorView,
    LocalOrderActionResponse,
    LocalOrderCancelRequest,
    LocalOrderCloseRequest,
    LocalOrderCreate,
    LocalOrderDiscountRequest,
    LocalOrderItemCreate,
    LocalOrderItemUpdate,
    LocalOrderListResponse,
    LocalOrderLoginRequest,
    LocalOrderLoginResponse,
    LocalOrderOperationRequest,
    LocalOrderPartialPaymentRequest,
    LocalOrderPrintResponse,
    LocalOrderTransferRequest,
    LocalOrderView,
    LocalProductFamilyListResponse,
    LocalProductListResponse,
)
from agent_local.orders.service import LocalOrderService
from agent_local.orders.ui import render_orders_ui
from agent_local.tray_app import is_agent_running, restart_agent, start_agent, stop_agent
from agent_local.windows_autostart import find_process_ids


DEFAULT_TOKEN_FILE = Path("agent_local/data/local_api_token.txt")
DEFAULT_ORDER_DB = Path("agent_local/data/local_orders.db")
DEFAULT_PRINT_JOBS_DIR = Path("agent_local/data/print_jobs")
ENV_FILE = Path(".env")
DEFAULT_LOCAL_API_HOST = "0.0.0.0"
DEFAULT_LOCAL_API_PORT = 8765
CLIENT_ONLINE_WINDOW = timedelta(minutes=5)

APP_NAME = "Movi_commanda"
DEFAULT_APP_VERSION = "1.0.0"
DEFAULT_VERSION_CODE = "100"

app = FastAPI(title="Movi_commanda Local API")
_connected_clients: dict[str, dict[str, object]] = {}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _env_file_value(name: str) -> str | None:
    if not ENV_FILE.exists():
        return None
    prefix = f"{name}="
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        return stripped[len(prefix):].strip().strip('"').strip("'")
    return None


def _config_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is not None and value.strip():
        return value.strip()
    value = _env_file_value(name)
    if value is not None and value.strip():
        return value.strip()
    return default


def _package_version() -> str:
    for candidate in (Path("package-version.txt"), Path("VERSAO_INSTALADA.txt")):
        if candidate.exists():
            value = candidate.read_text(encoding="utf-8").strip()
            if value:
                return value
    return _config_value("LOCAL_COMMAND_APP_VERSION", DEFAULT_APP_VERSION) or DEFAULT_APP_VERSION


def _version_code() -> str:
    return _config_value("LOCAL_COMMAND_VERSION_CODE", DEFAULT_VERSION_CODE) or DEFAULT_VERSION_CODE


def _token_file() -> Path:
    return Path(_config_value("LOCAL_API_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)) or DEFAULT_TOKEN_FILE)


def _read_token() -> str | None:
    token_file = _token_file()
    if not token_file.exists():
        return None
    token = token_file.read_text(encoding="ascii").strip()
    return token or None


def _is_loopback_client(request: Request) -> bool:
    client_ip = request.client.host if request.client else ""
    return client_ip in {"127.0.0.1", "::1", "localhost", "testclient"}


def _require_token(x_local_token: str | None = Header(default=None, alias="X-Local-Token")) -> None:
    token = _read_token()
    if not token:
        return
    if x_local_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local token invalid.",
        )


def _require_order_session(
    x_order_session: str | None = Header(default=None, alias="X-Order-Session"),
):
    if not x_order_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao de usuario obrigatoria.",
        )
    session = _order_service().get_session(x_order_session)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao de usuario invalida ou expirada.",
        )
    return session


def _empresa_id() -> str:
    empresa_id = (_config_value("AGENT_EMPRESA_ID") or "").strip()
    if not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AGENT_EMPRESA_ID nao configurado.",
        )
    return empresa_id


def _order_repository() -> LocalOrderRepository:
    return LocalOrderRepository(_config_value("LOCAL_ORDER_DB_PATH", str(DEFAULT_ORDER_DB)) or DEFAULT_ORDER_DB)


def _order_service() -> LocalOrderService:
    return LocalOrderService(_order_repository(), _empresa_id())


def _print_jobs_dir() -> Path:
    return Path(_config_value("LOCAL_ORDER_PRINT_JOBS_DIR", str(DEFAULT_PRINT_JOBS_DIR)) or DEFAULT_PRINT_JOBS_DIR)


def _receipt_width() -> int:
    raw_width = _config_value("LOCAL_ORDER_RECEIPT_WIDTH", "32") or "32"
    try:
        return int(raw_width)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LOCAL_ORDER_RECEIPT_WIDTH invalido.") from None


def _local_api_port() -> int:
    raw_port = _config_value("LOCAL_API_PORT", str(DEFAULT_LOCAL_API_PORT)) or str(DEFAULT_LOCAL_API_PORT)
    try:
        return int(raw_port)
    except ValueError:
        return DEFAULT_LOCAL_API_PORT


def _selected_local_ip() -> str | None:
    configured = _config_value("LOCAL_COMMAND_SELECTED_IP")
    if configured:
        return configured
    addresses = _detect_local_addresses()
    return addresses[0]["ip"] if addresses else None


def _detect_local_addresses() -> list[dict[str, str]]:
    addresses: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(ip: str, label: str) -> None:
        if not ip or ip in seen or ip.startswith("127.") or ip.startswith("169.254."):
            return
        seen.add(ip)
        addresses.append({"ip": ip, "label": label})

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            add(probe.getsockname()[0], "rota principal")
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for item in socket.getaddrinfo(hostname, None, socket.AF_INET):
            add(str(item[4][0]), hostname)
    except OSError:
        pass

    if os.name == "nt":
        try:
            command = (
                "Get-NetIPConfiguration | "
                "Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' "
                "-and $_.InterfaceAlias -notmatch 'vEthernet|Virtual|VMware|VirtualBox|Docker|WSL|Loopback|Bluetooth' } | "
                "ForEach-Object { $_.InterfaceAlias + '|' + $_.IPv4Address.IPAddress }"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=6,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in result.stdout.splitlines():
                if "|" not in line:
                    continue
                label, ip = line.split("|", 1)
                add(ip.strip(), label.strip())
        except Exception:
            pass

    return addresses


def _database_service() -> LocalDatabaseConfigService:
    return LocalDatabaseConfigService()


def _database_config_response(config: LocalDatabaseConfig) -> LocalDatabaseConfigResponse:
    return LocalDatabaseConfigResponse(
        database_type=config.database_type,
        host=config.host,
        port=config.port,
        database=config.database,
        username=config.username,
        password_configured=bool(config.password),
        ssl_enabled=config.ssl_enabled,
    )


def _load_database_config() -> LocalDatabaseConfig:
    mariadb_url = _config_value("AGENT_MARIADB_URL")
    if mariadb_url:
        try:
            return parse_mariadb_url(mariadb_url)
        except Exception:
            pass
    return LocalDatabaseConfig(
        database_type=DEFAULT_DATABASE_TYPE,
        host=DEFAULT_MARIADB_HOST,
        port=DEFAULT_MARIADB_PORT,
        database="",
        username=DEFAULT_MARIADB_USERNAME,
        password=DEFAULT_MARIADB_PASSWORD,
    )


def _require_technical_admin(session) -> None:
    _order_repository().require_permission(session.operator_code, "technical.admin")


def _safe_status(status_value: str, message: str, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"status": status_value, "message": message}
    payload.update(extra)
    return payload


def _client_status(last_seen_at: datetime) -> str:
    return "online" if _utc_now() - last_seen_at <= CLIENT_ONLINE_WINDOW else "offline"


@app.middleware("http")
async def track_connected_client(request: Request, call_next):
    response = await call_next(request)
    client_ip = request.client.host if request.client else ""
    if client_ip:
        session_token = request.headers.get("X-Order-Session")
        operator_code = None
        operator_name = None
        if session_token:
            try:
                session = _order_service().get_session(session_token)
                if session:
                    operator_code = session.operator_code
                    operator_name = session.operator_name
            except Exception:
                pass
        _connected_clients[client_ip] = {
            "ip": client_ip,
            "device_name": request.headers.get("X-Device-Name"),
            "user_agent": request.headers.get("User-Agent"),
            "operator_code": operator_code,
            "operator_name": operator_name,
            "last_seen_at": _utc_now(),
        }
    return response


def _refresh_order_catalog_from_server() -> None:
    enabled = (_config_value("LOCAL_ORDER_AUTO_REFRESH_CATALOG", "true") or "true").lower()
    if enabled in {"0", "false", "no", "nao"}:
        return
    mariadb_url = _config_value("AGENT_MARIADB_URL")
    if not mariadb_url:
        return
    try:
        client = MariaDBClient(mariadb_url=mariadb_url, source_query=_config_value("AGENT_SOURCE_QUERY"))
        catalog = client.fetch_order_catalog()
        _order_repository().upsert_catalog(
            operators=catalog.get("operators", []),
            products=catalog.get("products", []),
        )
    except Exception:
        return


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/orders/app-info", response_model=LocalCommandaAppInfoResponse)
def order_app_info(_: None = Depends(_require_token)) -> LocalCommandaAppInfoResponse:
    return LocalCommandaAppInfoResponse(
        app_name=APP_NAME,
        version_name=_package_version(),
        version_code=_version_code(),
    )


@app.get("/orders/local-token")
def order_local_token(request: Request) -> dict[str, object]:
    if not _is_loopback_client(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token local disponivel apenas no servidor.")
    token = _read_token()
    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token local nao encontrado.")
    return {"token": token}


@app.get("/orders/settings", response_model=LocalCommandaSettingsResponse)
def get_order_settings(_: None = Depends(_require_token)) -> LocalCommandaSettingsResponse:
    settings = _order_service().get_settings().model_copy(
        update={"versao_app": _package_version(), "codigo_versao": _version_code()}
    )
    return LocalCommandaSettingsResponse(settings=settings)


@app.put("/orders/settings", response_model=LocalCommandaSettingsResponse)
def save_order_settings(
    payload: LocalCommandaSettings,
    _: None = Depends(_require_token),
) -> LocalCommandaSettingsResponse:
    try:
        settings = _order_service().save_settings(payload)
    except Exception as exc:
        _order_repository().log_operation(
            empresa_id=_empresa_id(),
            session=type("Session", (), {"operator_code": "system", "operator_name": "system"})(),
            operation_type="settings.error",
            reason=str(exc),
        )
        raise _handle_order_error(exc) from exc
    return LocalCommandaSettingsResponse(settings=settings)


@app.post("/orders/settings/test-connection")
def test_order_server_connection(_: None = Depends(_require_token)) -> dict[str, object]:
    settings = _order_service().get_settings()
    return {
        "status": "ok",
        "message": "Configuracao local carregada.",
        "host": settings.ip_servidor,
        "port": settings.porta_servidor,
    }


@app.post("/orders/settings/load-server-data")
def load_order_server_data(_: None = Depends(_require_token)) -> dict[str, object]:
    try:
        _refresh_order_catalog_from_server()
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return {"status": "ok", "message": "Carga de dados solicitada."}


@app.get("/orders/license")
def get_order_license(_: None = Depends(_require_token)) -> dict[str, object]:
    settings = _order_service().get_settings()
    return {"license": settings.licenca or "", "status": "configured" if settings.licenca else "missing"}


@app.post("/orders/license/validate")
def validate_order_license(_: None = Depends(_require_token)) -> dict[str, object]:
    settings = _order_service().get_settings()
    return {
        "status": "valid" if settings.licenca else "missing",
        "message": "Licenca informada." if settings.licenca else "Licenca nao configurada.",
    }


@app.get("/orders/technical/network", response_model=LocalNetworkInfoResponse)
def technical_network_info(_: None = Depends(_require_token)) -> LocalNetworkInfoResponse:
    port = _local_api_port()
    selected_ip = _selected_local_ip()
    addresses = [
        LocalNetworkAddressView(
            ip=item["ip"],
            label=item["label"],
            url=f"http://{item['ip']}:{port}/orders/ui",
            selected=item["ip"] == selected_ip,
        )
        for item in _detect_local_addresses()
    ]
    return LocalNetworkInfoResponse(
        host=_config_value("LOCAL_API_HOST", DEFAULT_LOCAL_API_HOST) or DEFAULT_LOCAL_API_HOST,
        port=port,
        selected_ip=selected_ip,
        access_url=f"http://{selected_ip}:{port}/orders/ui" if selected_ip else None,
        addresses=addresses,
    )


@app.get("/orders/technical/clients", response_model=LocalConnectedClientListResponse)
def technical_connected_clients(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalConnectedClientListResponse:
    _require_technical_admin(session)
    clients: list[LocalConnectedClientView] = []
    for item in _connected_clients.values():
        last_seen_at = item["last_seen_at"]
        if not isinstance(last_seen_at, datetime):
            continue
        clients.append(
            LocalConnectedClientView(
                ip=str(item["ip"]),
                device_name=str(item["device_name"]) if item.get("device_name") else None,
                user_agent=str(item["user_agent"]) if item.get("user_agent") else None,
                operator_code=str(item["operator_code"]) if item.get("operator_code") else None,
                operator_name=str(item["operator_name"]) if item.get("operator_name") else None,
                last_seen_at=last_seen_at,
                status=_client_status(last_seen_at),
            )
        )
    clients.sort(key=lambda client: client.last_seen_at, reverse=True)
    return LocalConnectedClientListResponse(clients=clients)


@app.get("/orders/technical/database", response_model=LocalDatabaseConfigResponse)
def technical_get_database_config(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalDatabaseConfigResponse:
    _require_technical_admin(session)
    return _database_config_response(_load_database_config())


@app.post("/orders/technical/database/test")
def technical_test_database_config(
    payload: LocalDatabaseConfigPayload,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> dict[str, object]:
    _require_technical_admin(session)
    current = _load_database_config()
    password = payload.password if payload.password is not None else current.password
    config = LocalDatabaseConfig(
        database_type=payload.database_type,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        password=password or "",
        ssl_enabled=payload.ssl_enabled,
    )
    try:
        _database_service().test_connection(config)
        return _safe_status("connected", "Banco conectado.")
    except Exception as exc:
        _order_repository().log_operation(
            empresa_id=_empresa_id(),
            session=session,
            operation_type="technical.database_test",
            reason="erro ao testar banco",
            details={"status": "error", "error": exc.__class__.__name__},
        )
        return _safe_status("error", f"Erro ao conectar banco: {exc.__class__.__name__}")


@app.put("/orders/technical/database", response_model=LocalDatabaseConfigResponse)
def technical_save_database_config(
    payload: LocalDatabaseConfigPayload,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalDatabaseConfigResponse:
    _require_technical_admin(session)
    current = _load_database_config()
    password = payload.password if payload.password is not None else current.password
    config = LocalDatabaseConfig(
        database_type=payload.database_type,
        host=payload.host,
        port=payload.port,
        database=payload.database,
        username=payload.username,
        password=password or "",
        ssl_enabled=payload.ssl_enabled,
    )
    try:
        _database_service().test_connection(config)
        _database_service().save_config(config=config, env_file=str(ENV_FILE))
        _order_repository().log_operation(
            empresa_id=_empresa_id(),
            session=session,
            operation_type="technical.database_save",
            reason="configuracao de banco atualizada",
            details={
                "database_type": config.database_type,
                "host": config.host,
                "port": config.port,
                "database": config.database,
                "username": config.username,
                "ssl_enabled": config.ssl_enabled,
            },
        )
        return _database_config_response(config)
    except Exception as exc:
        _order_repository().log_operation(
            empresa_id=_empresa_id(),
            session=session,
            operation_type="technical.database_save_error",
            reason="erro ao salvar banco",
            details={"status": "error", "error": exc.__class__.__name__},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erro ao salvar banco: {exc.__class__.__name__}") from exc


@app.post("/orders/technical/check", response_model=LocalConnectionCheckResponse)
def technical_connection_check(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalConnectionCheckResponse:
    _require_technical_admin(session)
    server_api = _safe_status("connected", "API local conectada.", host=_config_value("LOCAL_API_HOST", DEFAULT_LOCAL_API_HOST), port=_local_api_port())
    database_config = _load_database_config()
    try:
        if not database_config.host or not database_config.database or not database_config.username:
            database = _safe_status("configuration_invalid", "Configuracao de banco incompleta.")
        else:
            _database_service().test_connection(database_config)
            database = _safe_status("connected", "Banco conectado.")
    except Exception as exc:
        database = _safe_status("error", f"Erro ao conectar banco: {exc.__class__.__name__}")

    printer_name = _config_value("LOCAL_ORDER_PRINTER_NAME")
    printer = (
        _safe_status("configured", "Impressora configurada.", printer_name=printer_name)
        if printer_name
        else _safe_status("configuration_invalid", "Impressora nao configurada.")
    )
    _order_repository().log_operation(
        empresa_id=_empresa_id(),
        session=session,
        operation_type="technical.connection_check",
        reason="verificacao de conexao",
        details={"server_api": server_api["status"], "database": database["status"], "printer": printer["status"]},
    )
    return LocalConnectionCheckResponse(server_api=server_api, database=database, printer=printer)


@app.get("/orders/technical/status")
def technical_server_status(_: None = Depends(_require_token)) -> dict[str, object]:
    network = technical_network_info(_)
    return {
        "status": "ok",
        "app_name": APP_NAME,
        "version": _package_version(),
        "network": network.model_dump(mode="json"),
        "sync_running": is_agent_running(),
        "clients_count": len(_connected_clients),
    }


@app.post("/orders/technical/restart-service")
def technical_restart_service(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> dict[str, object]:
    _require_technical_admin(session)
    try:
        if os.name == "nt":
            subprocess.Popen(
                ["wscript.exe", "//nologo", str(Path("Iniciar_Movi_commanda_Windows.vbs").resolve())],
                cwd=Path.cwd(),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen([os.sys.executable, "-m", "agent_local.windows_autostart"], cwd=Path.cwd())
        result = _safe_status("scheduled", "Reinicio do servico solicitado.")
    except Exception as exc:
        result = _safe_status("error", f"Erro ao reiniciar servico: {exc.__class__.__name__}")
    _order_repository().log_operation(
        empresa_id=_empresa_id(),
        session=session,
        operation_type="technical.restart_service",
        reason=str(result["message"]),
        details={"status": result["status"]},
    )
    return result


@app.get("/status")
def status_view() -> dict[str, object]:
    return {
        "status": "running",
        "sync_running": is_agent_running(),
        "api_pids": find_process_ids("agent_local.local_api"),
        "tray_pids": find_process_ids("agent_local.tray_app"),
        "sync_pids": find_process_ids("agent_local.main"),
    }


@app.post("/sync/start")
def start_sync(_: None = Depends(_require_token)) -> dict[str, str]:
    return {"status": start_agent()}


@app.post("/sync/stop")
def stop_sync(_: None = Depends(_require_token)) -> dict[str, str]:
    return {"status": stop_agent()}


@app.post("/sync/restart")
def restart_sync(_: None = Depends(_require_token)) -> dict[str, str]:
    return {"status": restart_agent()}


@app.post("/orders", response_model=LocalOrderView, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: LocalOrderCreate,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    if not payload.operator_code:
        payload = payload.model_copy(
            update={"operator_code": session.operator_code, "operator_name": session.operator_name}
        )
    return LocalOrderView.model_validate(_order_service().create_order(payload))


@app.post("/orders/confirm", response_model=LocalOrderView, status_code=status.HTTP_201_CREATED)
def confirm_order(
    payload: LocalOrderCreate,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    return create_order(payload, _, session)


def _handle_order_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda ou item nao encontrado.")
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro local de comanda.")


@app.post("/orders/{order_uuid}/items", response_model=LocalOrderView)
def add_order_item(
    order_uuid: str,
    payload: LocalOrderItemCreate,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    try:
        return LocalOrderView.model_validate(_order_service().add_item(order_uuid, payload))
    except Exception as exc:
        raise _handle_order_error(exc) from exc


@app.patch("/orders/{order_uuid}/items/{item_id}", response_model=LocalOrderView)
def update_order_item(
    order_uuid: str,
    item_id: int,
    payload: LocalOrderItemUpdate,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    try:
        return LocalOrderView.model_validate(_order_service().update_item(order_uuid, item_id, payload))
    except Exception as exc:
        raise _handle_order_error(exc) from exc


@app.delete("/orders/{order_uuid}/items/{item_id}", response_model=LocalOrderView)
def remove_order_item(
    order_uuid: str,
    item_id: int,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    try:
        return LocalOrderView.model_validate(_order_service().remove_item(order_uuid, item_id))
    except Exception as exc:
        raise _handle_order_error(exc) from exc


@app.delete("/orders/{order_uuid}/items", response_model=LocalOrderView)
def clear_order_items(
    order_uuid: str,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    try:
        return LocalOrderView.model_validate(_order_service().clear_items(order_uuid))
    except Exception as exc:
        raise _handle_order_error(exc) from exc


@app.post("/orders/{order_uuid}/close", response_model=LocalOrderView)
def close_order(
    order_uuid: str,
    payload: LocalOrderCloseRequest,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    try:
        return LocalOrderView.model_validate(_order_service().close_order(order_uuid, payload))
    except Exception as exc:
        raise _handle_order_error(exc) from exc


@app.post("/orders/{order_uuid}/cancel", response_model=LocalOrderView)
def cancel_order(
    order_uuid: str,
    payload: LocalOrderCancelRequest,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderView:
    try:
        return LocalOrderView.model_validate(_order_service().cancel_order(order_uuid, payload))
    except Exception as exc:
        raise _handle_order_error(exc) from exc


@app.get("/orders/operators", response_model=LocalOperatorListResponse)
def list_order_operators(_: None = Depends(_require_token)) -> LocalOperatorListResponse:
    _refresh_order_catalog_from_server()
    return LocalOperatorListResponse(operators=_order_service().list_operators())


@app.get("/orders/users", response_model=LocalOperatorListResponse)
def list_order_users(_: None = Depends(_require_token)) -> LocalOperatorListResponse:
    _refresh_order_catalog_from_server()
    return LocalOperatorListResponse(operators=_order_service().list_operators())


@app.post("/orders/login", response_model=LocalOrderLoginResponse)
def login_order_user(
    payload: LocalOrderLoginRequest,
    _: None = Depends(_require_token),
) -> LocalOrderLoginResponse:
    try:
        session = _order_service().authenticate_operator(payload.operator_code, payload.password)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return LocalOrderLoginResponse(
        session_token=session.token,
        operator=LocalOperatorView(code=session.operator_code, name=session.operator_name),
    )


@app.get("/orders/product-families", response_model=LocalProductFamilyListResponse)
def list_order_product_families(_: None = Depends(_require_token)) -> LocalProductFamilyListResponse:
    _refresh_order_catalog_from_server()
    return LocalProductFamilyListResponse(families=_order_service().list_product_families())


@app.get("/orders/products", response_model=LocalProductListResponse)
def list_order_products(
    family: str | None = Query(default=None, max_length=160),
    q: str | None = Query(default=None, max_length=160),
    _: None = Depends(_require_token),
) -> LocalProductListResponse:
    _refresh_order_catalog_from_server()
    return LocalProductListResponse(products=_order_service().list_products(family=family, query=q))


@app.get("/orders/me", response_model=LocalOperatorContextResponse)
def current_order_user(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOperatorContextResponse:
    return LocalOperatorContextResponse(
        operator=LocalOperatorView(code=session.operator_code, name=session.operator_name),
        permissions=_order_service().list_permissions(session.operator_code),
    )


@app.get("/orders", response_model=LocalOrderListResponse)
def list_orders(
    table_reference: str | None = Query(default=None, max_length=40),
    _: None = Depends(_require_token),
) -> LocalOrderListResponse:
    orders = [
        LocalOrderView.model_validate(order)
        for order in _order_service().list_orders(table_reference=table_reference)
    ]
    return LocalOrderListResponse(total=len(orders), orders=orders)


def _summary_payload(summary: dict[str, object]) -> dict[str, object]:
    order = summary["order"]
    return {
        "order": LocalOrderView.model_validate(order).model_dump(mode="json"),
        "subtotal": str(summary["subtotal"]),
        "discounts": str(summary["discounts"]),
        "partial_payments": str(summary["partial_payments"]),
        "total": str(summary["total"]),
        "remaining": str(summary["remaining"]),
    }


@app.get("/orders/current", response_model=LocalOrderActionResponse)
def current_order(
    order_uuid: str | None = Query(default=None, max_length=80),
    command_number: str | None = Query(default=None, max_length=40),
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        summary = _order_service().order_summary(order_uuid=order_uuid, command_number=command_number)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(status="ok", message="Comanda localizada.", payload=_summary_payload(summary))


@app.get("/orders/subtotal", response_model=LocalOrderActionResponse)
def order_subtotal(
    order_uuid: str | None = Query(default=None, max_length=80),
    command_number: str | None = Query(default=None, max_length=40),
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        summary = _order_service().order_summary(order_uuid=order_uuid, command_number=command_number)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(status="ok", message="Subtotal consultado.", payload=_summary_payload(summary))


@app.get("/orders/account", response_model=LocalOrderActionResponse)
def order_account(
    order_uuid: str | None = Query(default=None, max_length=80),
    command_number: str | None = Query(default=None, max_length=40),
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        summary = _order_service().order_summary(order_uuid=order_uuid, command_number=command_number)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(status="ok", message="Conta consultada.", payload=_summary_payload(summary))


@app.post("/orders/void", response_model=LocalOrderActionResponse)
def void_order_or_item(
    payload: LocalOrderOperationRequest,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        order = _order_service().void_order_or_item(payload, session)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(
        status="ok",
        message="Anulacao registrada.",
        order=LocalOrderView.model_validate(order),
    )


@app.post("/orders/transfer", response_model=LocalOrderActionResponse)
def transfer_order(
    payload: LocalOrderTransferRequest,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        order = _order_service().transfer_order(payload, session)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(
        status="ok",
        message="Transferencia registrada.",
        order=LocalOrderView.model_validate(order),
    )


@app.post("/orders/partial-payment", response_model=LocalOrderActionResponse)
def partial_payment(
    payload: LocalOrderPartialPaymentRequest,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        summary = _order_service().record_partial_payment(payload, session)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(status="ok", message="Pagamento parcial registrado.", payload=_summary_payload(summary))


@app.post("/orders/discount", response_model=LocalOrderActionResponse)
def discount_order(
    payload: LocalOrderDiscountRequest,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderActionResponse:
    try:
        summary = _order_service().apply_discount(payload, session)
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderActionResponse(status="ok", message="Desconto registrado.", payload=_summary_payload(summary))


@app.get("/orders/messages")
def list_messages(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> dict[str, object]:
    return {"messages": _order_service().list_messages(session.operator_code)}


@app.get("/orders/outbox")
def list_outbox(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> dict[str, object]:
    return {"events": _order_service().list_outbox()}


@app.post("/orders/voice-command")
def voice_command_stub(
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> dict[str, object]:
    return {
        "status": "planned",
        "message": "Estrutura preparada. Reconhecimento de voz ainda nao esta habilitado neste pacote local.",
    }


@app.get("/orders/{order_uuid}/prebill", response_class=HTMLResponse)
def order_prebill(order_uuid: str, _: None = Depends(_require_token)) -> str:
    try:
        order = _order_repository().get_by_uuid(empresa_id=_empresa_id(), order_uuid=order_uuid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda nao encontrada.") from None

    item_rows = "\n".join(
        f"""
        <tr>
          <td>{item.quantity}</td>
          <td>{escape(item.description)}<br><small>{escape(item.notes or '')}</small></td>
          <td>{item.unit_price}</td>
          <td>{item.line_total}</td>
        </tr>
        """
        for item in order.items
    )
    payment_rows = "\n".join(
        f"""
        <tr>
          <td>{escape(payment.payment_method)}</td>
          <td>{payment.amount}</td>
        </tr>
        """
        for payment in order.payments
    )
    payment_section = (
        f"""
  <h2>Pagamentos</h2>
  <table>
    <thead><tr><th>Forma</th><th>Valor</th></tr></thead>
    <tbody>{payment_rows}</tbody>
  </table>
        """
        if payment_rows
        else ""
    )
    table_label = f"Mesa {order.table_reference}" if order.table_reference else "Mesa nao informada"
    return f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Pre-conta - Comanda {escape(order.command_number)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; color: #111827; }}
    h1 {{ font-size: 22px; margin: 0 0 8px; }}
    .meta {{ margin-bottom: 16px; line-height: 1.5; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #d1d5db; padding: 8px; text-align: left; }}
    th:nth-child(1), td:nth-child(1) {{ width: 70px; }}
    th:nth-child(3), td:nth-child(3), th:nth-child(4), td:nth-child(4) {{ text-align: right; }}
    small {{ color: #4b5563; }}
    .total {{ text-align: right; font-size: 18px; margin-top: 14px; font-weight: 700; }}
    @media print {{ button {{ display: none; }} body {{ margin: 0; }} }}
  </style>
</head>
<body>
  <button onclick="window.print()">Imprimir pre-conta</button>
  <h1>Comanda {escape(order.command_number)}</h1>
  <div class="meta">
    <div>{escape(table_label)}</div>
    <div>Operador: {escape(order.operator_name or order.operator_code or 'Nao informado')}</div>
    <div>Status: {escape(order.status)}</div>
  </div>
  <table>
    <thead><tr><th>Qtd</th><th>Item</th><th>Unit.</th><th>Subtotal</th></tr></thead>
    <tbody>{item_rows}</tbody>
  </table>
  {payment_section}
  <div class="total">Total final: {order.total_amount}</div>
</body>
</html>
"""


@app.get("/orders/{order_uuid}/thermal-receipt", response_class=PlainTextResponse)
def order_thermal_receipt(order_uuid: str, _: None = Depends(_require_token)) -> str:
    try:
        order = _order_repository().get_by_uuid(empresa_id=_empresa_id(), order_uuid=order_uuid)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comanda nao encontrada.") from None
    return render_thermal_receipt(order, width=_receipt_width())


@app.post("/orders/{order_uuid}/print", response_model=LocalOrderPrintResponse)
def print_order(
    order_uuid: str,
    _: None = Depends(_require_token),
    session=Depends(_require_order_session),
) -> LocalOrderPrintResponse:
    try:
        job = _order_service().print_order(
            order_uuid,
            jobs_dir=_print_jobs_dir(),
            printer_name=_config_value("LOCAL_ORDER_PRINTER_NAME"),
            width=_receipt_width(),
        )
    except Exception as exc:
        raise _handle_order_error(exc) from exc
    return LocalOrderPrintResponse(
        order_uuid=job.order_uuid,
        status=job.status,
        printer_name=job.printer_name,
        job_path=str(job.job_path),
        message=job.message,
    )


@app.get("/orders/ui", response_class=HTMLResponse)
def orders_ui() -> str:
    return render_orders_ui()


