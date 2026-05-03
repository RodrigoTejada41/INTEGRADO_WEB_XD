from __future__ import annotations

import sqlite3
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from agent_local.orders.schemas import LocalOrderCloseRequest, LocalOrderCreate, LocalOrderItemCreate, LocalOrderItemUpdate


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


def _verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
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
            connection.execute("PRAGMA foreign_keys = ON")
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
    ) -> StoredOrder:
        self.initialize()
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

    def upsert_catalog(self, *, operators: list[dict[str, str]], products: list[dict[str, str]]) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO local_order_operators (code, name, active)
                VALUES (?, ?, 1)
                ON CONFLICT(code) DO UPDATE SET name = excluded.name, active = 1
                """,
                [
                    (operator["code"], operator["name"])
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
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
