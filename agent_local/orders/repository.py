from __future__ import annotations

import sqlite3
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from agent_local.orders.schemas import (
    LocalOrderCloseRequest,
    LocalCommandaSettings,
    LocalOrderCreate,
    LocalOrderDiscountRequest,
    LocalOrderItemCreate,
    LocalOrderItemUpdate,
    LocalOrderOperationRequest,
    LocalOrderPartialPaymentRequest,
    LocalOrderTransferRequest,
)


@dataclass(frozen=True)
class StoredOrderItem:
    id: int
    product_code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    notes: str | None


@dataclass(frozen=True)
class StoredOrderPayment:
    payment_method: str
    amount: Decimal


@dataclass(frozen=True)
class StoredOrderPrintGroup:
    family: str
    printer_name: str | None
    items: list[StoredOrderItem]


@dataclass(frozen=True)
class StoredOrder:
    uuid: str
    empresa_id: str
    command_number: str
    people_count: int | None
    table_reference: str | None
    operator_code: str | None
    operator_name: str | None
    customer_name: str | None
    status: str
    sync_status: str
    total_amount: Decimal
    payment_method: str | None
    amount_paid: Decimal | None
    closed_at: datetime | None
    cancel_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[StoredOrderItem]
    payments: list[StoredOrderPayment]


@dataclass(frozen=True)
class StoredOrderSession:
    token: str
    operator_code: str
    operator_name: str
    expires_at: datetime


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def hash_order_password(password: str, *, iterations: int = 210_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _looks_like_sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def hash_imported_order_password(password: str) -> str:
    cleaned = password.strip()
    if _looks_like_sha256_hex(cleaned):
        return f"xd_sha256${cleaned.lower()}"
    return hash_order_password(cleaned)


def _verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        if stored_hash.startswith("xd_sha256$"):
            expected_hex = stored_hash.split("$", 1)[1]
            actual_hex = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(actual_hex, expected_hex)
        algorithm, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_raw),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class LocalOrderRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL UNIQUE,
                    empresa_id TEXT NOT NULL,
                    command_number TEXT NULL,
                    people_count INTEGER NULL,
                    table_reference TEXT NULL,
                    operator_code TEXT NULL,
                    operator_name TEXT NULL,
                    customer_name TEXT NULL,
                    status TEXT NOT NULL,
                    sync_status TEXT NOT NULL,
                    total_amount TEXT NOT NULL,
                    payment_method TEXT NULL,
                    amount_paid TEXT NULL,
                    closed_at TEXT NULL,
                    cancel_reason TEXT NULL,
                    notes TEXT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_uuid TEXT NOT NULL REFERENCES local_orders(uuid) ON DELETE CASCADE,
                    product_code TEXT NOT NULL,
                    description TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    unit_price TEXT NOT NULL,
                    line_total TEXT NOT NULL,
                    notes TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_uuid TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    sync_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    synced_at TEXT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_xd_sync (
                    order_uuid TEXT PRIMARY KEY,
                    sale_zone_area_object_id INTEGER NOT NULL,
                    order_number INTEGER NOT NULL,
                    synced_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_uuid TEXT NOT NULL REFERENCES local_orders(uuid) ON DELETE CASCADE,
                    payment_method TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_operators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_sessions (
                    token TEXT PRIMARY KEY,
                    operator_code TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_operator_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operator_code TEXT NOT NULL,
                    permission TEXT NOT NULL,
                    allowed INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(operator_code, permission)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_commanda_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    empresa_id TEXT NOT NULL,
                    operator_code TEXT NOT NULL,
                    operator_name TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    order_uuid TEXT NULL,
                    command_number TEXT NULL,
                    item_id INTEGER NULL,
                    reason TEXT NULL,
                    details TEXT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operator_code TEXT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    read_at TEXT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_partial_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_uuid TEXT NOT NULL REFERENCES local_orders(uuid) ON DELETE CASCADE,
                    operator_code TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    selected_item_ids TEXT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_discounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_uuid TEXT NOT NULL REFERENCES local_orders(uuid) ON DELETE CASCADE,
                    operator_code TEXT NOT NULL,
                    discount_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_voids (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_uuid TEXT NOT NULL,
                    item_id INTEGER NULL,
                    operator_code TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_order_uuid TEXT NULL,
                    source_command_number TEXT NULL,
                    item_id INTEGER NULL,
                    destination_command_number TEXT NULL,
                    destination_table_reference TEXT NULL,
                    transfer_type TEXT NOT NULL,
                    operator_code TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_code TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    family TEXT NOT NULL,
                    unit_price TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_order_group_printers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family TEXT NOT NULL UNIQUE,
                    printer_name TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._add_column_if_missing(connection, "local_orders", "command_number", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "people_count", "INTEGER NULL")
            self._add_column_if_missing(connection, "local_orders", "table_reference", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "operator_code", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "operator_name", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "payment_method", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "amount_paid", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "closed_at", "TEXT NULL")
            self._add_column_if_missing(connection, "local_orders", "cancel_reason", "TEXT NULL")
            self._add_column_if_missing(connection, "local_order_items", "notes", "TEXT NULL")
            self._add_column_if_missing(connection, "local_order_operators", "password_hash", "TEXT NULL")
            self._seed_default_settings(connection)
            connection.commit()

    def create(self, empresa_id: str, payload: LocalOrderCreate) -> StoredOrder:
        self.initialize()
        order_uuid = str(uuid4())
        now = _utc_now_text()
        command_number = payload.command_number or self._next_command_number(empresa_id)
        operator_name = payload.operator_name
        if payload.operator_code:
            stored_operator = self.get_operator(payload.operator_code)
            if stored_operator:
                operator_name = stored_operator["name"]
        items = []
        total = Decimal("0")
        for item in payload.items:
            line_total = _to_money(item.quantity * item.unit_price)
            total += line_total
            items.append(
                StoredOrderItem(
                    id=0,
                    product_code=item.product_code,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=line_total,
                    notes=item.notes,
                )
            )
        total = _to_money(total)

        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO local_orders (
                    uuid, empresa_id, command_number, people_count, table_reference,
                    operator_code, operator_name, customer_name, status, sync_status,
                    total_amount, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_uuid,
                    empresa_id,
                    command_number,
                    payload.people_count,
                    payload.table_reference,
                    payload.operator_code,
                    operator_name,
                    payload.customer_name,
                    "draft",
                    "pending",
                    str(total),
                    payload.notes,
                    now,
                    now,
                ),
            )
            connection.executemany(
                """
                INSERT INTO local_order_items (
                    order_uuid, product_code, description, quantity, unit_price, line_total, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        order_uuid,
                        item.product_code,
                        item.description,
                        str(item.quantity),
                        str(item.unit_price),
                        str(item.line_total),
                        item.notes,
                    )
                    for item in items
                ],
            )
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.created", "pending", now),
            )
            connection.commit()

        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def add_item(self, *, empresa_id: str, order_uuid: str, payload: LocalOrderItemCreate) -> StoredOrder:
        self.initialize()
        self._ensure_order_editable(empresa_id=empresa_id, order_uuid=order_uuid)
        line_total = _to_money(payload.quantity * payload.unit_price)
        now = _utc_now_text()
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id, quantity, unit_price
                FROM local_order_items
                WHERE order_uuid = ?
                  AND product_code = ?
                  AND COALESCE(notes, '') = COALESCE(?, '')
                ORDER BY id
                LIMIT 1
                """,
                (order_uuid, payload.product_code, payload.notes),
            ).fetchone()
            if existing is not None:
                quantity = Decimal(str(existing["quantity"])) + payload.quantity
                unit_price = payload.unit_price
                line_total = _to_money(quantity * unit_price)
                connection.execute(
                    """
                    UPDATE local_order_items
                    SET quantity = ?, unit_price = ?, line_total = ?
                    WHERE id = ? AND order_uuid = ?
                    """,
                    (str(quantity), str(unit_price), str(line_total), int(existing["id"]), order_uuid),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO local_order_items (
                        order_uuid, product_code, description, quantity, unit_price, line_total, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_uuid,
                        payload.product_code,
                        payload.description,
                        str(payload.quantity),
                        str(payload.unit_price),
                        str(line_total),
                        payload.notes,
                    ),
                )
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.item.added", "pending", now),
            )
            connection.commit()
        self._recalculate_total(order_uuid)
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def clear_items(self, *, empresa_id: str, order_uuid: str) -> StoredOrder:
        self.initialize()
        self._ensure_order_editable(empresa_id=empresa_id, order_uuid=order_uuid)
        with self._connect() as connection:
            connection.execute("DELETE FROM local_order_items WHERE order_uuid = ?", (order_uuid,))
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.items.cleared", "pending", _utc_now_text()),
            )
            connection.commit()
        self._recalculate_total(order_uuid)
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def update_item(
        self,
        *,
        empresa_id: str,
        order_uuid: str,
        item_id: int,
        payload: LocalOrderItemUpdate,
    ) -> StoredOrder:
        self.initialize()
        self._ensure_order_editable(empresa_id=empresa_id, order_uuid=order_uuid)
        with self._connect() as connection:
            item = connection.execute(
                """
                SELECT quantity, unit_price, notes
                FROM local_order_items
                WHERE id = ? AND order_uuid = ?
                """,
                (item_id, order_uuid),
            ).fetchone()
            if item is None:
                raise KeyError(f"item:{item_id}")
            quantity = payload.quantity if payload.quantity is not None else Decimal(str(item["quantity"]))
            unit_price = payload.unit_price if payload.unit_price is not None else Decimal(str(item["unit_price"]))
            notes = payload.notes if payload.notes is not None else item["notes"]
            line_total = _to_money(quantity * unit_price)
            now = _utc_now_text()
            connection.execute(
                """
                UPDATE local_order_items
                SET quantity = ?, unit_price = ?, line_total = ?, notes = ?
                WHERE id = ? AND order_uuid = ?
                """,
                (str(quantity), str(unit_price), str(line_total), notes, item_id, order_uuid),
            )
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.item.updated", "pending", now),
            )
            connection.commit()
        self._recalculate_total(order_uuid)
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def remove_item(self, *, empresa_id: str, order_uuid: str, item_id: int) -> StoredOrder:
        self.initialize()
        self._ensure_order_editable(empresa_id=empresa_id, order_uuid=order_uuid)
        with self._connect() as connection:
            existing_count = connection.execute(
                "SELECT COUNT(*) AS total FROM local_order_items WHERE order_uuid = ?",
                (order_uuid,),
            ).fetchone()["total"]
            if int(existing_count) <= 1:
                raise ValueError("Comanda deve manter pelo menos um item.")
            cursor = connection.execute(
                "DELETE FROM local_order_items WHERE id = ? AND order_uuid = ?",
                (item_id, order_uuid),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"item:{item_id}")
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.item.removed", "pending", _utc_now_text()),
            )
            connection.commit()
        self._recalculate_total(order_uuid)
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def close_order(
        self,
        *,
        empresa_id: str,
        order_uuid: str,
        payload: LocalOrderCloseRequest,
        session: StoredOrderSession,
    ) -> StoredOrder:
        self.initialize()
        self.require_permission(session.operator_code, "order.close")
        self._ensure_order_editable(empresa_id=empresa_id, order_uuid=order_uuid)
        order = self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)
        payments = self._normalize_close_payments(payload)
        amount_paid = _to_money(sum((payment.amount for payment in payments), Decimal("0")))
        if amount_paid < order.total_amount:
            raise ValueError("Valor pago menor que o total da comanda.")
        payment_method = " + ".join(dict.fromkeys(payment.payment_method for payment in payments))
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute("DELETE FROM local_order_payments WHERE order_uuid = ?", (order_uuid,))
            connection.executemany(
                """
                INSERT INTO local_order_payments (order_uuid, payment_method, amount, created_at)
                VALUES (?, ?, ?, ?)
                """,
                [(order_uuid, payment.payment_method, str(payment.amount), now) for payment in payments],
            )
            connection.execute(
                """
                UPDATE local_orders
                SET status = ?, payment_method = ?, amount_paid = ?, closed_at = ?, updated_at = ?
                WHERE empresa_id = ? AND uuid = ?
                """,
                ("closed", payment_method, str(amount_paid), now, now, empresa_id, order_uuid),
            )
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.closed", "pending", now),
            )
            connection.commit()
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def cancel_order(self, *, empresa_id: str, order_uuid: str, reason: str | None) -> StoredOrder:
        self.initialize()
        self._ensure_order_editable(empresa_id=empresa_id, order_uuid=order_uuid)
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE local_orders
                SET status = ?, cancel_reason = ?, updated_at = ?
                WHERE empresa_id = ? AND uuid = ?
                """,
                ("cancelled", reason, now, empresa_id, order_uuid),
            )
            connection.execute(
                """
                INSERT INTO local_order_outbox (order_uuid, event_type, sync_status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_uuid, "order.cancelled", "pending", now),
            )
            connection.commit()
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)

    def list(self, empresa_id: str, table_reference: str | None = None) -> list[StoredOrder]:
        self.initialize()
        params: list[str] = [empresa_id]
        where = "WHERE empresa_id = ?"
        if table_reference:
            where += " AND table_reference = ?"
            params.append(table_reference)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT uuid
                FROM local_orders
                {where}
                ORDER BY created_at DESC, id DESC
                """,
                params,
            ).fetchall()
        return [self.get_by_uuid(empresa_id=empresa_id, order_uuid=str(row["uuid"])) for row in rows]

    def get_by_uuid(self, *, empresa_id: str, order_uuid: str) -> StoredOrder:
        self.initialize()
        with self._connect() as connection:
            order = connection.execute(
                """
                SELECT uuid, empresa_id, command_number, people_count, table_reference,
                       operator_code, operator_name, customer_name, status, sync_status,
                       total_amount, payment_method, amount_paid, closed_at, cancel_reason,
                       notes, created_at, updated_at
                FROM local_orders
                WHERE empresa_id = ? AND uuid = ?
                """,
                (empresa_id, order_uuid),
            ).fetchone()
            if order is None:
                raise KeyError(order_uuid)
            item_rows = connection.execute(
                """
                SELECT id, product_code, description, quantity, unit_price, line_total
                       , notes
                FROM local_order_items
                WHERE order_uuid = ?
                ORDER BY id
                """,
                (order_uuid,),
            ).fetchall()
            payment_rows = connection.execute(
                """
                SELECT payment_method, amount
                FROM local_order_payments
                WHERE order_uuid = ?
                ORDER BY id
                """,
                (order_uuid,),
            ).fetchall()

        return StoredOrder(
            uuid=str(order["uuid"]),
            empresa_id=str(order["empresa_id"]),
            command_number=str(order["command_number"] or ""),
            people_count=int(order["people_count"]) if order["people_count"] is not None else None,
            table_reference=order["table_reference"],
            operator_code=order["operator_code"],
            operator_name=order["operator_name"],
            customer_name=order["customer_name"],
            status=str(order["status"]),
            sync_status=str(order["sync_status"]),
            total_amount=Decimal(str(order["total_amount"])),
            payment_method=order["payment_method"],
            amount_paid=Decimal(str(order["amount_paid"])) if order["amount_paid"] is not None else None,
            closed_at=_parse_datetime(str(order["closed_at"])) if order["closed_at"] is not None else None,
            cancel_reason=order["cancel_reason"],
            notes=order["notes"],
            created_at=_parse_datetime(str(order["created_at"])),
            updated_at=_parse_datetime(str(order["updated_at"])),
            items=[
                StoredOrderItem(
                    id=int(item["id"]),
                    product_code=str(item["product_code"]),
                    description=str(item["description"]),
                    quantity=Decimal(str(item["quantity"])),
                    unit_price=Decimal(str(item["unit_price"])),
                    line_total=Decimal(str(item["line_total"])),
                    notes=item["notes"],
                )
                for item in item_rows
            ],
            payments=[
                StoredOrderPayment(
                    payment_method=str(payment["payment_method"]),
                    amount=Decimal(str(payment["amount"])),
                )
                for payment in payment_rows
            ],
        )

    def list_operators(self) -> list[dict[str, str]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT code, name
                FROM local_order_operators
                WHERE active = 1
                ORDER BY name
                """
            ).fetchall()
        return [{"code": str(row["code"]), "name": str(row["name"])} for row in rows]

    def authenticate_operator(self, code: str, password: str, *, ttl_hours: int = 12) -> StoredOrderSession:
        self.initialize()
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=ttl_hours)
        with self._connect() as connection:
            operator = connection.execute(
                """
                SELECT code, name, password_hash
                FROM local_order_operators
                WHERE code = ? AND active = 1
                """,
                (code,),
            ).fetchone()
            if operator is None or not _verify_password(password, operator["password_hash"]):
                raise PermissionError("Usuario ou senha invalido.")
            token = secrets.token_urlsafe(32)
            connection.execute("DELETE FROM local_order_sessions WHERE expires_at <= ?", (now.isoformat(),))
            connection.execute(
                """
                INSERT INTO local_order_sessions (token, operator_code, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, str(operator["code"]), now.isoformat(), expires_at.isoformat()),
            )
            connection.commit()
        return StoredOrderSession(
            token=token,
            operator_code=str(operator["code"]),
            operator_name=str(operator["name"]),
            expires_at=expires_at,
        )

    def get_session(self, token: str) -> StoredOrderSession | None:
        self.initialize()
        now = datetime.now(UTC)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT s.token, s.operator_code, s.expires_at, o.name AS operator_name
                FROM local_order_sessions s
                INNER JOIN local_order_operators o ON o.code = s.operator_code
                WHERE s.token = ? AND s.expires_at > ? AND o.active = 1
                """,
                (token, now.isoformat()),
            ).fetchone()
        if row is None:
            return None
        return StoredOrderSession(
            token=str(row["token"]),
            operator_code=str(row["operator_code"]),
            operator_name=str(row["operator_name"]),
            expires_at=_parse_datetime(str(row["expires_at"])),
        )

    def set_operator_password(self, code: str, password: str) -> None:
        self.initialize()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE local_order_operators SET password_hash = ? WHERE code = ? AND active = 1",
                (hash_order_password(password), code),
            )
            if cursor.rowcount == 0:
                raise KeyError(code)
            connection.commit()

    def list_permissions(self, operator_code: str) -> dict[str, bool]:
        self.initialize()
        defaults = {
            "order.create": True,
            "order.close": True,
            "order.void": True,
            "order.transfer": True,
            "order.partial_payment": True,
            "order.discount": True,
            "order.print": True,
            "order.messages": True,
            "technical.admin": True,
        }
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT permission, allowed
                FROM local_order_operator_permissions
                WHERE operator_code = ?
                """,
                (operator_code,),
            ).fetchall()
        permissions = defaults.copy()
        permissions.update({str(row["permission"]): bool(row["allowed"]) for row in rows})
        return permissions

    def get_settings(self) -> LocalCommandaSettings:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute("SELECT key, value FROM local_commanda_settings").fetchall()
        data = {str(row["key"]): row["value"] for row in rows}
        return LocalCommandaSettings(**data)

    def save_settings(self, payload: LocalCommandaSettings) -> LocalCommandaSettings:
        self.initialize()
        data = payload.model_dump(mode="json")
        if not data.get("ip_servidor"):
            raise ValueError("Endereco IP obrigatorio.")
        if not data.get("porta_servidor"):
            raise ValueError("Porta obrigatoria.")
        now = _utc_now_text()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO local_commanda_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                [(key, "" if value is None else str(value), now) for key, value in data.items()],
            )
            connection.commit()
        return self.get_settings()

    def _seed_default_settings(self, connection: sqlite3.Connection) -> None:
        now = _utc_now_text()
        defaults = {
            "ip_servidor": "127.0.0.1",
            "porta_servidor": "8765",
            "licenca": "",
            "ssid_wifi": "",
            "impressora_bluetooth": "",
            "dpi_impressora": "203",
            "largura_impressora": "58",
            "caracteres_por_linha": "32",
            "tema_interface": "padrao",
            "usuario_logado": "",
            "versao_app": "1.0.0",
            "codigo_versao": "100",
        }
        connection.executemany(
            """
            INSERT OR IGNORE INTO local_commanda_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            [(key, value, now) for key, value in defaults.items()],
        )

    def require_permission(self, operator_code: str, permission: str) -> None:
        if not self.list_permissions(operator_code).get(permission, False):
            raise PermissionError(f"Permissao negada: {permission}")

    def get_by_command_number(self, *, empresa_id: str, command_number: str) -> StoredOrder:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT uuid
                FROM local_orders
                WHERE empresa_id = ? AND command_number = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (empresa_id, command_number),
            ).fetchone()
        if row is None:
            raise KeyError(command_number)
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=str(row["uuid"]))

    def resolve_order(self, *, empresa_id: str, order_uuid: str | None, command_number: str | None) -> StoredOrder:
        if order_uuid:
            return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order_uuid)
        if command_number:
            return self.get_by_command_number(empresa_id=empresa_id, command_number=command_number)
        raise ValueError("Informe comanda.")

    def log_operation(
        self,
        *,
        empresa_id: str,
        session: StoredOrderSession,
        operation_type: str,
        order_uuid: str | None = None,
        command_number: str | None = None,
        item_id: int | None = None,
        reason: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_order_operation_logs (
                    empresa_id, operator_code, operator_name, operation_type,
                    order_uuid, command_number, item_id, reason, details, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    empresa_id,
                    session.operator_code,
                    session.operator_name,
                    operation_type,
                    order_uuid,
                    command_number,
                    item_id,
                    reason,
                    json.dumps(details or {}, ensure_ascii=True, default=str),
                    _utc_now_text(),
                ),
            )
            connection.commit()

    def order_financial_summary(
        self,
        *,
        empresa_id: str,
        order_uuid: str | None,
        command_number: str | None,
    ) -> dict[str, object]:
        order = self.resolve_order(empresa_id=empresa_id, order_uuid=order_uuid, command_number=command_number)
        with self._connect() as connection:
            discount_row = connection.execute(
                """
                SELECT COALESCE(SUM(CAST(amount AS NUMERIC)), 0) AS total
                FROM local_order_discounts
                WHERE order_uuid = ?
                """,
                (order.uuid,),
            ).fetchone()
            partial_row = connection.execute(
                """
                SELECT COALESCE(SUM(CAST(amount AS NUMERIC)), 0) AS total
                FROM local_order_partial_payments
                WHERE order_uuid = ?
                """,
                (order.uuid,),
            ).fetchone()
        discounts = _to_money(Decimal(str(discount_row["total"] or "0")))
        partial_payments = _to_money(Decimal(str(partial_row["total"] or "0")))
        final_total = max(_to_money(order.total_amount - discounts), Decimal("0.00"))
        remaining = max(_to_money(final_total - partial_payments), Decimal("0.00"))
        return {
            "order": order,
            "subtotal": order.total_amount,
            "discounts": discounts,
            "partial_payments": partial_payments,
            "total": final_total,
            "remaining": remaining,
        }

    def record_partial_payment(
        self,
        *,
        empresa_id: str,
        session: StoredOrderSession,
        payload: LocalOrderPartialPaymentRequest,
    ) -> dict[str, object]:
        self.require_permission(session.operator_code, "order.partial_payment")
        order = self.resolve_order(
            empresa_id=empresa_id,
            order_uuid=payload.order_uuid,
            command_number=payload.command_number,
        )
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_order_partial_payments (
                    order_uuid, operator_code, payment_method, amount, selected_item_ids, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order.uuid,
                    session.operator_code,
                    payload.payment_method,
                    str(_to_money(payload.amount)),
                    json.dumps(payload.selected_item_ids or [], ensure_ascii=True),
                    now,
                ),
            )
            connection.commit()
        self.log_operation(
            empresa_id=empresa_id,
            session=session,
            operation_type="partial_payment",
            order_uuid=order.uuid,
            command_number=order.command_number,
            details={"payment_method": payload.payment_method, "amount": str(_to_money(payload.amount))},
        )
        return self.order_financial_summary(empresa_id=empresa_id, order_uuid=order.uuid, command_number=None)

    def apply_discount(
        self,
        *,
        empresa_id: str,
        session: StoredOrderSession,
        payload: LocalOrderDiscountRequest,
    ) -> dict[str, object]:
        self.require_permission(session.operator_code, "order.discount")
        order = self.resolve_order(
            empresa_id=empresa_id,
            order_uuid=payload.order_uuid,
            command_number=payload.command_number,
        )
        if payload.discount_type == "percent":
            amount = _to_money(order.total_amount * (payload.value / Decimal("100")))
        else:
            amount = _to_money(payload.value)
        if amount > order.total_amount:
            raise ValueError("Desconto maior que o subtotal da comanda.")
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_order_discounts (
                    order_uuid, operator_code, discount_type, value, amount, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (order.uuid, session.operator_code, payload.discount_type, str(payload.value), str(amount), payload.reason, now),
            )
            connection.commit()
        self.log_operation(
            empresa_id=empresa_id,
            session=session,
            operation_type="discount",
            order_uuid=order.uuid,
            command_number=order.command_number,
            reason=payload.reason,
            details={"discount_type": payload.discount_type, "value": str(payload.value), "amount": str(amount)},
        )
        return self.order_financial_summary(empresa_id=empresa_id, order_uuid=order.uuid, command_number=None)

    def void_order_or_item(
        self,
        *,
        empresa_id: str,
        session: StoredOrderSession,
        payload: LocalOrderOperationRequest,
    ) -> StoredOrder:
        self.require_permission(session.operator_code, "order.void")
        if not payload.reason:
            raise ValueError("Motivo da anulacao obrigatorio.")
        order = self.resolve_order(
            empresa_id=empresa_id,
            order_uuid=payload.order_uuid,
            command_number=payload.command_number,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_order_voids (order_uuid, item_id, operator_code, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order.uuid, payload.item_id, session.operator_code, payload.reason, _utc_now_text()),
            )
            connection.commit()
        if payload.item_id:
            result = self.remove_item(empresa_id=empresa_id, order_uuid=order.uuid, item_id=payload.item_id)
        else:
            result = self.cancel_order(empresa_id=empresa_id, order_uuid=order.uuid, reason=payload.reason)
        self.log_operation(
            empresa_id=empresa_id,
            session=session,
            operation_type="void",
            order_uuid=order.uuid,
            command_number=order.command_number,
            item_id=payload.item_id,
            reason=payload.reason,
        )
        return result

    def transfer_order(
        self,
        *,
        empresa_id: str,
        session: StoredOrderSession,
        payload: LocalOrderTransferRequest,
    ) -> StoredOrder:
        self.require_permission(session.operator_code, "order.transfer")
        order = self.resolve_order(
            empresa_id=empresa_id,
            order_uuid=payload.source_order_uuid,
            command_number=payload.source_command_number,
        )
        if payload.transfer_type == "item":
            if not payload.item_id or not payload.destination_command_number:
                raise ValueError("Transferencia de item exige item e comanda destino.")
        if payload.transfer_type in {"command", "table"} and not (
            payload.destination_command_number or payload.destination_table_reference
        ):
            raise ValueError("Informe destino da transferencia.")
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_order_transfers (
                    source_order_uuid, source_command_number, item_id,
                    destination_command_number, destination_table_reference,
                    transfer_type, operator_code, reason, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.uuid,
                    order.command_number,
                    payload.item_id,
                    payload.destination_command_number,
                    payload.destination_table_reference,
                    payload.transfer_type,
                    session.operator_code,
                    payload.reason,
                    now,
                ),
            )
            if payload.transfer_type in {"command", "table"}:
                connection.execute(
                    """
                    UPDATE local_orders
                    SET command_number = COALESCE(?, command_number),
                        table_reference = COALESCE(?, table_reference),
                        updated_at = ?
                    WHERE empresa_id = ? AND uuid = ?
                    """,
                    (
                        payload.destination_command_number,
                        payload.destination_table_reference,
                        now,
                        empresa_id,
                        order.uuid,
                    ),
                )
            connection.commit()
        self.log_operation(
            empresa_id=empresa_id,
            session=session,
            operation_type="transfer",
            order_uuid=order.uuid,
            command_number=order.command_number,
            item_id=payload.item_id,
            reason=payload.reason,
            details={
                "transfer_type": payload.transfer_type,
                "destination_command_number": payload.destination_command_number,
                "destination_table_reference": payload.destination_table_reference,
            },
        )
        return self.get_by_uuid(empresa_id=empresa_id, order_uuid=order.uuid)

    def list_messages(self, operator_code: str) -> list[dict[str, object]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, title, body, read_at, created_at
                FROM local_order_messages
                WHERE operator_code IS NULL OR operator_code = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 50
                """,
                (operator_code,),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "title": str(row["title"]),
                "body": str(row["body"]),
                "read_at": row["read_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_outbox(self) -> list[dict[str, object]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, order_uuid, event_type, sync_status, created_at, synced_at
                FROM local_order_outbox
                ORDER BY created_at DESC, id DESC
                LIMIT 50
                """
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "order_uuid": row["order_uuid"],
                "event_type": row["event_type"],
                "sync_status": row["sync_status"],
                "created_at": row["created_at"],
                "synced_at": row["synced_at"],
            }
            for row in rows
        ]

    def get_xd_sync(self, order_uuid: str) -> dict[str, int] | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT sale_zone_area_object_id, order_number
                FROM local_order_xd_sync
                WHERE order_uuid = ?
                """,
                (order_uuid,),
            ).fetchone()
        if row is None:
            return None
        return {
            "sale_zone_area_object_id": int(row["sale_zone_area_object_id"]),
            "order_number": int(row["order_number"]),
        }

    def save_xd_sync(self, *, order_uuid: str, sale_zone_area_object_id: int, order_number: int) -> None:
        self.initialize()
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_order_xd_sync (
                    order_uuid, sale_zone_area_object_id, order_number, synced_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(order_uuid) DO UPDATE SET
                    sale_zone_area_object_id = excluded.sale_zone_area_object_id,
                    order_number = excluded.order_number,
                    synced_at = excluded.synced_at
                """,
                (order_uuid, sale_zone_area_object_id, order_number, now),
            )
            connection.commit()

    def mark_order_synced(self, order_uuid: str) -> None:
        self.initialize()
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute(
                "UPDATE local_orders SET sync_status = ?, updated_at = ? WHERE uuid = ?",
                ("synced", now, order_uuid),
            )
            connection.execute(
                """
                UPDATE local_order_outbox
                SET sync_status = ?, synced_at = ?
                WHERE order_uuid = ? AND sync_status = ?
                """,
                ("synced", now, order_uuid, "pending"),
            )
            connection.commit()

    def upsert_catalog(self, *, operators: list[dict[str, str]], products: list[dict[str, str]]) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO local_order_operators (code, name, password_hash, active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    password_hash = COALESCE(excluded.password_hash, local_order_operators.password_hash),
                    active = 1
                """,
                [
                    (
                        operator["code"],
                        operator["name"],
                        hash_imported_order_password(operator["password"]) if operator.get("password") else None,
                    )
                    for operator in operators
                    if operator.get("code") and operator.get("name")
                ],
            )
            connection.executemany(
                """
                INSERT INTO local_order_products (product_code, description, family, unit_price, active)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(product_code) DO UPDATE SET
                    description = excluded.description,
                    family = excluded.family,
                    unit_price = excluded.unit_price,
                    active = 1
                """,
                [
                    (
                        product["product_code"],
                        product["description"],
                        product.get("family") or "Geral",
                        str(product.get("unit_price") or "0"),
                    )
                    for product in products
                    if product.get("product_code") and product.get("description")
                ],
            )
            connection.commit()

    def get_operator(self, code: str) -> dict[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT code, name
                FROM local_order_operators
                WHERE code = ? AND active = 1
                """,
                (code,),
            ).fetchone()
        if row is None:
            return None
        return {"code": str(row["code"]), "name": str(row["name"])}

    def list_product_families(self) -> list[str]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT family
                FROM local_order_products
                WHERE active = 1
                ORDER BY family
                """
            ).fetchall()
        return [str(row["family"]) for row in rows]

    def list_products(self, family: str | None = None, query: str | None = None) -> list[dict[str, str]]:
        self.initialize()
        params: list[str] = []
        where = "WHERE active = 1"
        if family:
            where += " AND family = ?"
            params.append(family)
        if query:
            where += " AND (product_code LIKE ? OR description LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT product_code, description, family, unit_price
                FROM local_order_products
                {where}
                ORDER BY family, description
                LIMIT 300
                """,
                params,
            ).fetchall()
        return [
            {
                "product_code": str(row["product_code"]),
                "description": str(row["description"]),
                "family": str(row["family"]),
                "unit_price": str(row["unit_price"]),
            }
            for row in rows
        ]

    def list_group_printers(self) -> list[dict[str, object]]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT family, printer_name, active
                FROM local_order_group_printers
                ORDER BY family
                """
            ).fetchall()
        return [
            {"family": str(row["family"]), "printer_name": str(row["printer_name"]), "active": bool(row["active"])}
            for row in rows
        ]

    def save_group_printers(self, mappings: list[dict[str, object]]) -> list[dict[str, object]]:
        self.initialize()
        now = _utc_now_text()
        with self._connect() as connection:
            connection.execute("DELETE FROM local_order_group_printers")
            connection.executemany(
                """
                INSERT INTO local_order_group_printers (family, printer_name, active, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        str(item["family"]).strip(),
                        str(item["printer_name"]).strip(),
                        1 if item.get("active", True) else 0,
                        now,
                    )
                    for item in mappings
                    if str(item.get("family", "")).strip() and str(item.get("printer_name", "")).strip()
                ],
            )
            connection.commit()
        return self.list_group_printers()

    def order_print_groups(self, *, order: StoredOrder) -> list[StoredOrderPrintGroup]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT i.id, COALESCE(p.family, 'Geral') AS family, gp.printer_name
                FROM local_order_items i
                LEFT JOIN local_order_products p ON p.product_code = i.product_code
                INNER JOIN local_order_group_printers gp ON gp.family = COALESCE(p.family, 'Geral') AND gp.active = 1
                WHERE i.order_uuid = ?
                ORDER BY COALESCE(p.family, 'Geral'), i.id
                """,
                (order.uuid,),
            ).fetchall()
        items_by_id = {item.id: item for item in order.items}
        grouped: dict[str, StoredOrderPrintGroup] = {}
        for row in rows:
            item = items_by_id.get(int(row["id"]))
            if item is None:
                continue
            family = str(row["family"] or "Geral")
            current = grouped.get(family)
            if current is None:
                current = StoredOrderPrintGroup(family=family, printer_name=row["printer_name"], items=[])
                grouped[family] = current
            current.items.append(item)
        return list(grouped.values())

    def _next_command_number(self, empresa_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM local_orders WHERE empresa_id = ?",
                (empresa_id,),
            ).fetchone()
        return f"{int(row['total']) + 1:03d}"

    def _ensure_order_editable(self, *, empresa_id: str, order_uuid: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM local_orders WHERE empresa_id = ? AND uuid = ?",
                (empresa_id, order_uuid),
            ).fetchone()
        if row is None:
            raise KeyError(order_uuid)
        if str(row["status"]) in {"closed", "cancelled"}:
            raise RuntimeError("Comanda fechada ou cancelada nao pode ser alterada.")

    def _recalculate_total(self, order_uuid: str) -> None:
        now = _utc_now_text()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(CAST(line_total AS NUMERIC)), 0) AS total
                FROM local_order_items
                WHERE order_uuid = ?
                """,
                (order_uuid,),
            ).fetchone()
            total = _to_money(Decimal(str(row["total"] or "0")))
            connection.execute(
                """
                UPDATE local_orders
                SET total_amount = ?, updated_at = ?
                WHERE uuid = ?
                """,
                (str(total), now, order_uuid),
            )
            connection.commit()

    def _normalize_close_payments(self, payload: LocalOrderCloseRequest) -> list[StoredOrderPayment]:
        if payload.payments:
            return [
                StoredOrderPayment(payment_method=payment.payment_method, amount=_to_money(payment.amount))
                for payment in payload.payments
            ]
        if payload.payment_method and payload.amount_paid is not None:
            return [
                StoredOrderPayment(
                    payment_method=payload.payment_method,
                    amount=_to_money(payload.amount_paid),
                )
            ]
        raise ValueError("Informe pagamento unico ou lista de pagamentos.")

    def _add_column_if_missing(
        self, connection: sqlite3.Connection, table_name: str, column_name: str, column_sql: str
    ) -> None:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
