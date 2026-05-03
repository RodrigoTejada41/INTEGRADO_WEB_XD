from __future__ import annotations

import os
from pathlib import Path
from html import escape

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from agent_local.db.mariadb_client import MariaDBClient
from agent_local.orders.printer import render_thermal_receipt
from agent_local.orders.repository import LocalOrderRepository
from agent_local.orders.schemas import (
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

app = FastAPI(title="MoviSync Local Sync API")


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


def _token_file() -> Path:
    return Path(_config_value("LOCAL_API_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)) or DEFAULT_TOKEN_FILE)


def _read_token() -> str | None:
    token_file = _token_file()
    if not token_file.exists():
        return None
    token = token_file.read_text(encoding="ascii").strip()
    return token or None


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


def _refresh_order_catalog_from_xd() -> None:
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
    _refresh_order_catalog_from_xd()
    return LocalOperatorListResponse(operators=_order_service().list_operators())


@app.get("/orders/users", response_model=LocalOperatorListResponse)
def list_order_users(_: None = Depends(_require_token)) -> LocalOperatorListResponse:
    _refresh_order_catalog_from_xd()
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
    _refresh_order_catalog_from_xd()
    return LocalProductFamilyListResponse(families=_order_service().list_product_families())


@app.get("/orders/products", response_model=LocalProductListResponse)
def list_order_products(
    family: str | None = Query(default=None, max_length=160),
    q: str | None = Query(default=None, max_length=160),
    _: None = Depends(_require_token),
) -> LocalProductListResponse:
    _refresh_order_catalog_from_xd()
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


def _legacy_orders_ui_reference() -> str:
    return """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Comandas Locais</title>
  <style>
    :root { --blue: #213f78; --blue-dark: #0e4358; --green: #078d3e; --purple: #25106d; --purple-2: #32128a; --paper: #f7f7f7; }
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; margin: 0; color: #263238; background: #ffffff; }
    button, input, select, textarea { font: inherit; }
    button { border: 0; cursor: pointer; }
    .app-shell { min-height: 100vh; display: flex; flex-direction: column; background: #fff; }
    .status-bar { height: 34px; padding: 6px 22px; background: var(--blue-dark); color: white; display: flex; justify-content: space-between; font-weight: 700; letter-spacing: .02em; }
    .topbar { min-height: 74px; background: var(--blue); color: white; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 14px; padding: 10px 18px; }
    .back { font-size: 34px; line-height: 1; }
    .brand { display: flex; align-items: center; gap: 12px; }
    .logo { font-size: 44px; font-weight: 900; letter-spacing: -4px; }
    .title { font-size: 28px; font-weight: 800; line-height: 1.1; }
    .subtitle { font-size: 20px; font-weight: 400; opacity: .95; }
    .top-actions { display: flex; gap: 22px; font-size: 38px; }
    .screen-tabs { display: grid; grid-template-columns: repeat(3, 1fr); background: #102f61; }
    .screen-tabs button { min-height: 48px; color: white; background: transparent; font-weight: 800; border-bottom: 4px solid transparent; }
    .screen-tabs button.active { border-bottom-color: #7b1dc2; background: #1a3f7e; }
    .screen { display: none; }
    .screen.active { display: block; }
    .entry-row { display: grid; grid-template-columns: 1fr 1fr auto; gap: 14px; align-items: end; padding: 18px 20px 12px; }
    .field-line { border: 0; border-bottom: 3px solid #18889e; border-radius: 0; padding: 12px 0 8px; width: 100%; font-size: 26px; color: #555; background: transparent; text-transform: uppercase; }
    .continue-btn { min-height: 62px; min-width: 162px; background: var(--blue); color: white; font-size: 21px; font-weight: 800; border-radius: 4px; box-shadow: 0 5px 12px #0002; }
    .area-tabs { display: flex; border-bottom: 1px solid #ddd; padding-left: 0; overflow-x: auto; }
    .area-tabs button { min-width: 122px; height: 66px; background: white; color: #555; font-weight: 800; border-right: 1px solid #ddd; }
    .area-tabs button.active { border-bottom: 7px solid #4a0098; color: #333; }
    .command-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 5px; padding: 5px; }
    .command-tile { aspect-ratio: 1 / .98; background: var(--green); color: white; font-size: 28px; display: flex; align-items: center; padding: 18px; text-align: left; }
    .command-tile.selected { outline: 5px solid #f5c542; outline-offset: -5px; }
    .mesa-panel { padding: 24px 20px; min-height: 70vh; }
    .mesa-row { display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: end; }
    .ops-screen { min-height: calc(100vh - 156px); background: linear-gradient(180deg, #283484 0%, #2b0875 100%); color: white; padding: 18px 22px 28px; }
    .operator-strip { display: grid; grid-template-columns: 120px 1fr; gap: 14px; align-items: center; border-bottom: 1px solid #ffffff66; padding-bottom: 12px; margin-bottom: 24px; }
    .avatar { width: 112px; height: 112px; background: #fff; display: grid; place-items: center; color: #111; font-size: 56px; }
    .operator-name { text-align: center; margin-top: 8px; font-size: 20px; }
    .operator-actions { display: grid; grid-template-columns: 1fr; gap: 1px; }
    .operator-actions button { min-height: 56px; background: #243979; color: white; font-size: 20px; text-align: left; padding-left: 26px; border-bottom: 1px solid #ffffff55; }
    .voice-btn { width: 160px; height: 118px; margin: 32px auto; display: grid; place-items: center; background: #250c69; color: white; border-radius: 18px; font-weight: 700; }
    .voice-btn span { display: block; font-size: 42px; line-height: 1; }
    .menu-action-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
    .menu-action-grid button { min-height: 136px; background: #250c69; color: white; border-radius: 10px; font-size: 19px; font-weight: 700; box-shadow: 0 7px 12px #0002; }
    .menu-action-grid .icon { display: block; font-size: 38px; margin-bottom: 12px; }
    .work-area { padding: 0; background: #f4f6f9; color: #263238; }
    .work-grid { display: grid; grid-template-columns: minmax(280px, 360px) 1fr; gap: 18px; padding: 18px; }
    .panel { background: white; border: 1px solid #d7dee8; padding: 14px; }
    .compact-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .compact-grid .wide { grid-column: span 2; }
    label { display: block; font-size: 12px; font-weight: 700; color: #52616f; margin-bottom: 5px; text-transform: uppercase; }
    input, textarea, select { width: 100%; padding: 10px; border: 1px solid #aab7c4; background: white; }
    .product-board { background: #fff; min-height: calc(100vh - 160px); padding: 0 0 96px; }
    .product-board > label, .product-board .compact-grid { display: none; }
    .product-family-tabs { display: flex; overflow-x: auto; border-bottom: 1px solid #d7dee8; background: #fff; scrollbar-width: thin; }
    .product-family-tabs button { min-width: 150px; min-height: 64px; padding: 0 18px; background: #fff; color: #555; border-right: 1px solid #d7dee8; border-bottom: 7px solid transparent; font-size: 22px; font-weight: 800; white-space: nowrap; }
    .product-family-tabs button.active { border-bottom-color: #4a0098; color: #263238; }
    .product-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; padding: 5px; margin-bottom: 0; }
    .product-tile { min-height: 156px; aspect-ratio: 1 / .95; background: #3f5f90; color: #fff; border: 0; display: flex; align-items: center; justify-content: center; padding: 12px; text-align: center; font-size: 28px; font-weight: 500; line-height: 1.15; text-transform: uppercase; overflow-wrap: anywhere; }
    .product-tile:active { background: #314d79; }
    .product-bottom-bar { position: sticky; bottom: 0; display: grid; grid-template-columns: 2fr 1fr; min-height: 96px; background: #1f4a83ee; color: white; }
    .product-bottom-bar button { background: transparent; color: white; border-left: 1px solid #ffffff22; font-size: 22px; font-weight: 700; display: grid; place-items: center; }
    .product-bottom-bar span { display: block; font-size: 34px; line-height: 1; margin-bottom: 4px; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .toolbar button { min-height: 44px; background: var(--blue); color: white; padding: 8px 12px; font-weight: 700; }
    .toolbar .secondary { background: white; color: #263238; border: 1px solid #aab7c4; }
    .toolbar .danger { background: #9f1d1d; }
    table { width: 100%; border-collapse: collapse; background: white; }
    th, td { border-bottom: 1px solid #d9e2ec; padding: 8px; text-align: left; }
    .muted, .status { color: #52616f; font-size: 13px; margin: 8px 0; }
    .selected { background: #eef6ff; }
    @media (max-width: 760px) {
      .title { font-size: 24px; }
      .subtitle { font-size: 18px; }
      .entry-row { grid-template-columns: 1fr 1fr; }
      .continue-btn { grid-column: span 2; width: 100%; }
      .command-tile { font-size: 24px; }
      .menu-action-grid { gap: 12px; }
      .menu-action-grid button { min-height: 116px; font-size: 16px; }
      .work-grid { grid-template-columns: 1fr; }
      .product-family-tabs button { min-width: 122px; min-height: 58px; font-size: 19px; }
      .product-tile { min-height: 118px; font-size: 24px; }
    }
  </style>
</head>
<body>
<div class="app-shell">
  <div class="status-bar"><span>22:20</span><span>4G  Wi-Fi  bateria</span></div>
  <header class="topbar">
    <button class="back" type="button" onclick="showScreen('commands')">‹</button>
    <div class="brand">
      <div class="logo">XD</div>
      <div>
        <div id="screen-title" class="title">COMANDA</div>
        <div id="screen-subtitle" class="subtitle">Selecione o/a COMANDA.</div>
      </div>
    </div>
    <div class="top-actions"><button type="button" onclick="loadOrders()">⟳</button><button type="button" onclick="showScreen('work')">⌕</button></div>
  </header>
  <nav class="screen-tabs">
    <button id="tab-commands" type="button" class="active" onclick="showScreen('commands')">COMANDA</button>
    <button id="tab-table" type="button" onclick="showScreen('table')">MESA</button>
    <button id="tab-work" type="button" onclick="showScreen('work')">PEDIR</button>
  </nav>

  <section id="screen-commands" class="screen active">
    <form id="order-form">
      <div class="entry-row">
        <input class="field-line" name="command_number" placeholder="COMANDA">
        <input class="field-line" name="people_count" placeholder="Nº de Pessoas">
        <button class="continue-btn" type="button" onclick="showScreen('table')">CONTINUAR</button>
      </div>
      <div class="area-tabs">
        <button type="button" class="active">TODAS</button>
        <button type="button">BAR</button>
        <button type="button">SALA</button>
        <button type="button">ESPLANADA</button>
      </div>
      <div id="command-grid" class="command-grid">
        <button class="command-tile" type="button" onclick="pickCommand('1')">COMANDA 1</button>
        <button class="command-tile" type="button" onclick="pickCommand('2')">COMANDA 2</button>
        <button class="command-tile" type="button" onclick="pickCommand('3')">COMANDA 3</button>
        <button class="command-tile" type="button" onclick="pickCommand('4')">COMANDA 4</button>
        <button class="command-tile" type="button" onclick="pickCommand('5')">COMANDA 5</button>
        <button class="command-tile" type="button" onclick="pickCommand('6')">COMANDA 6</button>
        <button class="command-tile" type="button" onclick="pickCommand('7')">COMANDA 7</button>
        <button class="command-tile" type="button" onclick="pickCommand('8')">COMANDA 8</button>
        <button class="command-tile" type="button" onclick="pickCommand('9')">COMANDA 9</button>
      </div>
    </form>
  </section>

  <section id="screen-table" class="screen">
    <div class="mesa-panel">
      <div class="mesa-row">
        <input class="field-line" name="table_reference_proxy" placeholder="MESA">
        <button class="continue-btn" type="button" onclick="copyMesaAndGo()">CONTINUAR</button>
      </div>
      <input name="table_reference" hidden form="order-form">
    </div>
  </section>

  <section id="screen-work" class="screen">
    <div class="ops-screen">
      <div class="operator-strip">
        <div>
          <div class="avatar">●</div>
          <div id="operator-label" class="operator-name">SUPORTE</div>
        </div>
        <div class="operator-actions">
          <button type="button">⬆ CAIXA DE SAÍDA</button>
          <button type="button">▣ MENSAGENS</button>
        </div>
      </div>
      <button class="voice-btn" type="button"><span>♬</span>CONTROLE POR<br>VOZ</button>
      <div class="menu-action-grid">
        <button type="button" onclick="focusProduct()"><span class="icon">☑</span>PEDIR</button>
        <button type="button" onclick="cancelSelectedOrder()"><span class="icon">☒</span>ANULAR</button>
        <button type="button" onclick="printSelectedOrder()"><span class="icon">▤</span>SUBTOTAL</button>
        <button type="button" onclick="printSelectedOrder()"><span class="icon">▣</span>CONTA</button>
        <button type="button"><span class="icon">↔</span>TRANSFERÊNCIA</button>
        <button type="button" onclick="closeSelectedOrder()"><span class="icon">▭</span>PAGAMENTO PARCIAL</button>
        <button type="button" onclick="showScreen('commands')"><span class="icon">▤</span>OUTROS</button>
        <button type="button"><span class="icon">$</span>DESCONTO</button>
        <button type="button" onclick="showScreen('commands')"><span class="icon">←</span>MENU INICIAL</button>
      </div>
    </div>
    <div class="work-area">
      <div class="work-grid">
        <div class="panel">
          <div class="compact-grid">
            <div class="wide">
              <label>Operador</label>
              <select name="operator_code" form="order-form"></select>
            </div>
            <div class="wide">
              <label>Cliente</label>
              <input name="customer_name" autocomplete="off" form="order-form">
            </div>
            <div class="wide">
              <label>Token local</label>
              <input name="token" type="password" autocomplete="off" form="order-form">
            </div>
            <div class="wide">
              <label>Observação</label>
              <textarea name="notes" rows="2" form="order-form"></textarea>
            </div>
          </div>
          <div class="toolbar">
            <button type="submit" form="order-form" id="submit-button">Abrir comanda</button>
            <button type="button" class="secondary" onclick="newComanda()">Nova comanda</button>
            <button type="button" onclick="closeSelectedOrder()">Fechar comanda</button>
            <button type="button" class="danger" onclick="cancelSelectedOrder()">Cancelar comanda</button>
          </div>
          <div id="status" class="status"></div>
          <div id="selected-order" class="muted">Nenhuma comanda selecionada.</div>
        </div>
        <div class="panel product-board">
          <label>Famílias</label>
          <div id="families-carousel" class="product-family-tabs"></div>
          <div id="products" class="product-list"></div>
          <div class="compact-grid">
            <div><label>Código</label><input name="product_code" required form="order-form"></div>
            <div><label>Quantidade</label><input name="quantity" type="number" min="0.001" step="0.001" required form="order-form"></div>
            <div class="wide"><label>Descrição</label><input name="description" required form="order-form"></div>
            <div><label>Valor unitário</label><input name="unit_price" type="number" min="0" step="0.01" required form="order-form"></div>
            <div><label>Obs. item</label><input name="item_notes" placeholder="sem cebola, ponto da carne" form="order-form"></div>
          </div>
          <div class="product-bottom-bar">
            <button type="button" onclick="printSelectedOrder()"><span>▣</span>VER CONTEUDO DA MESA</button>
            <button type="button" onclick="showScreen('commands')"><span>✓</span>CONCLUIR</button>
          </div>
        </div>
      </div>
      <div class="panel">
        <table>
          <thead><tr><th>Item</th><th>Qtd</th><th>Unit.</th><th>Subtotal</th><th>Obs.</th><th>Ações</th></tr></thead>
          <tbody id="selected-items"></tbody>
        </table>
      </div>
      <div class="panel">
        <table>
          <thead><tr><th>Comanda</th><th>Mesa</th><th>Operador</th><th>Status</th><th>Total</th><th>Ações</th></tr></thead>
          <tbody id="orders"></tbody>
        </table>
      </div>
    </div>
  </section>
</div>
<script>
const form = document.getElementById('order-form');
const statusEl = document.getElementById('status');
const ordersEl = document.getElementById('orders');
const selectedOrderEl = document.getElementById('selected-order');
const selectedItemsEl = document.getElementById('selected-items');
const submitButton = document.getElementById('submit-button');
const operatorsEl = form.elements.operator_code;
const familiesEl = document.getElementById('families-carousel');
const productsEl = document.getElementById('products');
let selectedOrder = null;

function showScreen(name) {
  const titleMap = {
    commands: ['COMANDA', 'Selecione o/a COMANDA.'],
    table: ['MESA', 'Selecione o/a MESA.'],
    work: ['MENU', 'Operar comanda local.']
  };
  for (const item of ['commands', 'table', 'work']) {
    document.getElementById(`screen-${item}`).classList.toggle('active', item === name);
    document.getElementById(`tab-${item}`).classList.toggle('active', item === name);
  }
  document.getElementById('screen-title').textContent = titleMap[name][0];
  document.getElementById('screen-subtitle').textContent = titleMap[name][1];
}

function pickCommand(value) {
  form.elements.command_number.value = value;
  for (const tile of document.querySelectorAll('.command-tile')) {
    tile.classList.toggle('selected', tile.textContent.trim() === `COMANDA ${value}`);
  }
}

function copyMesaAndGo() {
  const mesa = document.querySelector('[name="table_reference_proxy"]').value;
  form.elements.table_reference.value = mesa;
  showScreen('work');
}

function focusProduct() {
  showScreen('work');
  form.elements.product_code.focus();
}

function printSelectedOrder() {
  if (!selectedOrder) {
    statusEl.textContent = 'Selecione uma comanda.';
    return;
  }
  printPrebill(selectedOrder.uuid);
}

function headers() {
  const token = form.elements.token.value;
  return token ? {'Content-Type': 'application/json', 'X-Local-Token': token} : {'Content-Type': 'application/json'};
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

async function loadOrders() {
  const response = await fetch('/orders', {headers: headers()});
  if (!response.ok) return;
  const data = await response.json();
  ordersEl.innerHTML = data.orders.map(order => `
    <tr class="${selectedOrder && selectedOrder.uuid === order.uuid ? 'selected' : ''}">
      <td>${escapeHtml(order.command_number)}</td>
      <td>${escapeHtml(order.table_reference)}</td>
      <td>${escapeHtml(order.operator_name || order.operator_code)}</td>
      <td>${escapeHtml(order.status)}</td>
      <td>${escapeHtml(order.total_amount)}</td>
      <td>
        <button type="button" onclick="selectOrder('${order.uuid}')">Usar</button>
        <button type="button" onclick="printPrebill('${order.uuid}')">Imprimir</button>
      </td>
    </tr>`).join('');
}

async function selectOrder(uuid) {
  const response = await fetch('/orders', {headers: headers()});
  if (!response.ok) return;
  const data = await response.json();
  selectedOrder = data.orders.find(order => order.uuid === uuid) || null;
  renderSelectedOrder();
  await loadOrders();
}

function renderSelectedOrder() {
  if (!selectedOrder) {
    selectedOrderEl.textContent = 'Nenhuma comanda selecionada.';
    selectedItemsEl.innerHTML = '';
    submitButton.textContent = 'Abrir comanda';
    return;
  }
  selectedOrderEl.textContent = `Comanda ${selectedOrder.command_number} | Mesa ${selectedOrder.table_reference || '-'} | Total ${selectedOrder.total_amount}`;
  submitButton.textContent = 'Adicionar item na comanda';
  selectedItemsEl.innerHTML = selectedOrder.items.map(item => `
    <tr>
      <td>${escapeHtml(item.description)}</td>
      <td><input id="qty-${item.id}" type="number" min="0.001" step="0.001" value="${escapeHtml(item.quantity)}"></td>
      <td>${escapeHtml(item.unit_price)}</td>
      <td>${escapeHtml(item.line_total)}</td>
      <td><input id="notes-${item.id}" value="${escapeHtml(item.notes)}"></td>
      <td>
        <button type="button" onclick="updateItem(${item.id})">Atualizar</button>
        <button type="button" class="danger" onclick="removeItem(${item.id})">Remover</button>
      </td>
    </tr>`).join('');
}

function newComanda() {
  selectedOrder = null;
  renderSelectedOrder();
}

async function updateItem(itemId) {
  if (!selectedOrder) return;
  const response = await fetch(`/orders/${selectedOrder.uuid}/items/${itemId}`, {
    method: 'PATCH',
    headers: headers(),
    body: JSON.stringify({
      quantity: document.getElementById(`qty-${itemId}`).value,
      notes: document.getElementById(`notes-${itemId}`).value
    })
  });
  statusEl.textContent = response.ok ? 'Item atualizado.' : await response.text();
  if (response.ok) {
    selectedOrder = await response.json();
    renderSelectedOrder();
    await loadOrders();
  }
}

async function removeItem(itemId) {
  if (!selectedOrder) return;
  const response = await fetch(`/orders/${selectedOrder.uuid}/items/${itemId}`, {
    method: 'DELETE',
    headers: headers()
  });
  statusEl.textContent = response.ok ? 'Item removido.' : await response.text();
  if (response.ok) {
    selectedOrder = await response.json();
    renderSelectedOrder();
    await loadOrders();
  }
}

async function closeSelectedOrder() {
  if (!selectedOrder) {
    statusEl.textContent = 'Selecione uma comanda.';
    return;
  }
  const raw = prompt('Pagamentos. Use: dinheiro=30,pix=40', `dinheiro=${selectedOrder.total_amount}`);
  if (!raw) return;
  const payments = raw.split(',').map(part => {
    const [payment_method, amount] = part.split('=').map(value => value.trim());
    return {payment_method, amount};
  }).filter(payment => payment.payment_method && payment.amount);
  const response = await fetch(`/orders/${selectedOrder.uuid}/close`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({payments})
  });
  statusEl.textContent = response.ok ? 'Comanda fechada.' : await response.text();
  if (response.ok) {
    selectedOrder = await response.json();
    renderSelectedOrder();
    await loadOrders();
  }
}

async function cancelSelectedOrder() {
  if (!selectedOrder) {
    statusEl.textContent = 'Selecione uma comanda.';
    return;
  }
  const reason = prompt('Motivo do cancelamento') || null;
  const response = await fetch(`/orders/${selectedOrder.uuid}/cancel`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({reason})
  });
  statusEl.textContent = response.ok ? 'Comanda cancelada.' : await response.text();
  if (response.ok) {
    selectedOrder = await response.json();
    renderSelectedOrder();
    await loadOrders();
  }
}

async function printPrebill(uuid) {
  const response = await fetch(`/orders/${uuid}/prebill`, {headers: headers()});
  if (!response.ok) {
    statusEl.textContent = await response.text();
    return;
  }
  const html = await response.text();
  const printWindow = window.open('', '_blank');
  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
}

async function loadOperators() {
  const response = await fetch('/orders/operators', {headers: headers()});
  operatorsEl.innerHTML = '<option value="">Operador manual/nao informado</option>';
  if (!response.ok) return;
  const data = await response.json();
  for (const operator of data.operators) {
    const option = document.createElement('option');
    option.value = operator.code;
    option.textContent = operator.name;
    operatorsEl.appendChild(option);
  }
}

async function loadFamilies() {
  const response = await fetch('/orders/product-families', {headers: headers()});
  if (!response.ok) return;
  const data = await response.json();
  familiesEl.innerHTML = data.families.map(family => `<button type="button" data-family="${escapeHtml(family)}">${escapeHtml(family)}</button>`).join('');
  for (const button of familiesEl.querySelectorAll('button')) {
    button.addEventListener('click', () => loadProducts(button.dataset.family));
  }
  if (data.families.length > 0) {
    await loadProducts(data.families[0]);
  }
}

async function loadProducts(family) {
  const response = await fetch(`/orders/products?family=${encodeURIComponent(family)}`, {headers: headers()});
  if (!response.ok) return;
  const data = await response.json();
  for (const button of familiesEl.querySelectorAll('button')) {
    button.classList.toggle('active', button.dataset.family === family);
  }
  productsEl.innerHTML = data.products.map(product => `
    <button class="product-tile" type="button" data-code="${escapeHtml(product.product_code)}" data-description="${escapeHtml(product.description)}" data-price="${escapeHtml(product.unit_price)}">
      ${escapeHtml(product.description)}
    </button>`).join('');
  for (const button of productsEl.querySelectorAll('button')) {
    button.addEventListener('click', () => {
      form.elements.product_code.value = button.dataset.code;
      form.elements.description.value = button.dataset.description;
      form.elements.unit_price.value = button.dataset.price;
      form.elements.quantity.value = form.elements.quantity.value || '1';
      if (!selectedOrder) {
        statusEl.textContent = 'Selecione ou abra uma comanda antes de pedir.';
        return;
      }
      form.requestSubmit();
    });
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = {
    command_number: form.elements.command_number.value || null,
    table_reference: form.elements.table_reference.value || null,
    operator_code: form.elements.operator_code.value || null,
    customer_name: form.elements.customer_name.value || null,
    notes: form.elements.notes.value || null,
    items: [{
      product_code: form.elements.product_code.value,
      description: form.elements.description.value,
      quantity: form.elements.quantity.value,
      unit_price: form.elements.unit_price.value,
      notes: form.elements.item_notes.value || null
    }]
  };
  const url = selectedOrder ? `/orders/${selectedOrder.uuid}/items` : '/orders';
  const method = 'POST';
  const body = selectedOrder ? JSON.stringify(payload.items[0]) : JSON.stringify(payload);
  const response = await fetch(url, {method, headers: headers(), body});
  statusEl.textContent = response.ok ? (selectedOrder ? 'Item adicionado.' : 'Comanda salva localmente.') : await response.text();
  if (response.ok) {
    if (selectedOrder) {
      selectedOrder = await response.json();
      renderSelectedOrder();
    }
    form.elements.product_code.value = '';
    form.elements.description.value = '';
    form.elements.quantity.value = '';
    form.elements.unit_price.value = '';
    form.elements.item_notes.value = '';
    await loadOrders();
  }
});

loadOperators();
loadFamilies();
loadOrders();
</script>
</body>
</html>
"""
