from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import create_engine, text

from agent_local.orders.repository import StoredOrder


ZERO_DATE = datetime(1, 1, 1)
ZERO_GUID = "00000000-0000-0000-0000-000000000000"


@dataclass(frozen=True)
class XDOrderSyncResult:
    sale_zone_area_object_id: int
    order_number: int


class XDOpenOrdersWriter:
    def __init__(self, mariadb_url: str, *, terminal_id: int = 1):
        self.engine = create_engine(mariadb_url, pool_pre_ping=True, future=True)
        self.terminal_id = terminal_id

    def sync_order(self, order: StoredOrder, *, order_number: int | None = None) -> XDOrderSyncResult:
        sale_zone_area_object_id = self._parse_command_number(order.command_number)
        with self.engine.begin() as connection:
            selected_order_number = order_number or self._resolve_order_number(connection, sale_zone_area_object_id)
            connection.execute(
                text(
                    """
                    DELETE FROM tmpdocumentstables
                    WHERE ParentGuid = :order_uuid
                    """
                ),
                {"order_uuid": order.uuid},
            )
            if order.status in {"cancelled", "closed"}:
                self._refresh_table_state(connection, sale_zone_area_object_id, context=None)
                return XDOrderSyncResult(sale_zone_area_object_id, selected_order_number)
            context = self._load_context(connection)
            user_id = self._resolve_user_id(connection, order.operator_code, order.operator_name, context["user_id"])
            created_at = _naive_datetime(order.created_at)
            rows = [
                self._build_line(
                    order=order,
                    item=item,
                    sale_zone_area_object_id=sale_zone_area_object_id,
                    order_number=selected_order_number,
                    sort_number=index,
                    context=context,
                    user_id=user_id,
                    created_at=created_at,
                    connection=connection,
                )
                for index, item in enumerate(order.items, start=1)
            ]
            if rows:
                columns = list(rows[0])
                connection.execute(
                    text(
                        f"""
                        INSERT INTO tmpdocumentstables (
                            {", ".join(f"`{column}`" for column in columns)}
                        )
                        VALUES (
                            {", ".join(f":{column}" for column in columns)}
                        )
                        """
                    ),
                    rows,
                )
            self._refresh_table_state(
                connection,
                sale_zone_area_object_id,
                context=context,
                created_at=created_at,
                people_count=order.people_count,
            )
            return XDOrderSyncResult(sale_zone_area_object_id, selected_order_number)

    def _resolve_order_number(self, connection, sale_zone_area_object_id: int) -> int:
        existing = connection.execute(
            text(
                """
                SELECT OrderNumber
                FROM tmpdocumentstables
                WHERE SaleZoneAreaObjectId = :sale_zone_area_object_id
                ORDER BY Id
                LIMIT 1
                """
            ),
            {"sale_zone_area_object_id": sale_zone_area_object_id},
        ).scalar()
        if existing is not None:
            return int(existing)
        counter = connection.execute(text("SELECT OrderCounter FROM xconfig LIMIT 1")).scalar()
        order_number = int(counter or 1)
        connection.execute(
            text("UPDATE xconfig SET OrderCounter = GREATEST(OrderCounter, :next_order_number)"),
            {"next_order_number": order_number + 1},
        )
        return order_number

    def _load_context(self, connection) -> dict[str, int]:
        xconfig = connection.execute(
            text(
                """
                SELECT Session, Shift, DefaultSerie, DefaultPaymentType, DefaultCurrency
                FROM xconfig
                LIMIT 1
                """
            )
        ).mappings().first()
        terminal = connection.execute(
            text(
                """
                SELECT DefaultUserId, IdShop, DefaultWarehouseId
                FROM xconfigterminals
                WHERE Id = :terminal_id
                LIMIT 1
                """
            ),
            {"terminal_id": self.terminal_id},
        ).mappings().first()
        return {
            "session": int((xconfig or {}).get("Session") or 0),
            "shift": int((xconfig or {}).get("Shift") or 1),
            "serie_id": int((xconfig or {}).get("DefaultSerie") or 1),
            "payment_type": int((xconfig or {}).get("DefaultPaymentType") or 1),
            "currency_id": int((xconfig or {}).get("DefaultCurrency") or 1),
            "user_id": int((terminal or {}).get("DefaultUserId") or 0),
            "id_shop": int((terminal or {}).get("IdShop") or 1),
            "warehouse_id": int((terminal or {}).get("DefaultWarehouseId") or 1),
        }

    def _refresh_table_state(
        self,
        connection,
        sale_zone_area_object_id: int,
        *,
        context: dict[str, int] | None,
        created_at: datetime | None = None,
        people_count: int | None = None,
    ) -> None:
        self._ensure_table_object(connection, sale_zone_area_object_id)
        summary = connection.execute(
            text(
                """
                SELECT COUNT(*) AS items,
                       COALESCE(SUM(TotalAmount), 0) AS total,
                       MIN(CreationDate) AS first_created
                FROM tmpdocumentstables
                WHERE SaleZoneAreaObjectId = :sale_zone_area_object_id
                """
            ),
            {"sale_zone_area_object_id": sale_zone_area_object_id},
        ).mappings().first()
        items_count = int((summary or {}).get("items") or 0)
        service_percent = self._service_percent(connection)
        if items_count <= 0:
            connection.execute(
                text(
                    """
                    UPDATE xconfigsalezonesareaobjects
                    SET Status = 0,
                        Total = 0,
                        LogoutDate = :closed_at,
                        NumberPersons = 0,
                        SyncStamp = CURRENT_TIMESTAMP
                    WHERE Id = :sale_zone_area_object_id
                    """
                ),
                {"sale_zone_area_object_id": sale_zone_area_object_id, "closed_at": datetime.now()},
            )
            return
        raw_total = Decimal(str((summary or {}).get("total") or "0"))
        visual_total = _money3(raw_total * (Decimal("1") + (service_percent / Decimal("100"))))
        login_date = created_at or (summary or {}).get("first_created") or datetime.now()
        connection.execute(
            text(
                """
                UPDATE xconfigsalezonesareaobjects
                SET Status = 1,
                    Total = :total,
                    CustomerKeyId = '0',
                    LoginDate = :login_date,
                    LogoutDate = :zero_date,
                    Terminal = :terminal_id,
                    NumberPersons = :people_count,
                    SyncStamp = CURRENT_TIMESTAMP
                WHERE Id = :sale_zone_area_object_id
                """
            ),
            {
                "sale_zone_area_object_id": sale_zone_area_object_id,
                "total": visual_total,
                "login_date": login_date,
                "zero_date": ZERO_DATE,
                "terminal_id": self.terminal_id,
                "people_count": int(people_count or 0),
            },
        )

    def _ensure_table_object(self, connection, sale_zone_area_object_id: int) -> None:
        exists = connection.execute(
            text("SELECT 1 FROM xconfigsalezonesareaobjects WHERE Id = :id LIMIT 1"),
            {"id": sale_zone_area_object_id},
        ).scalar()
        if exists:
            return
        connection.execute(
            text(
                """
                INSERT INTO xconfigsalezonesareaobjects (Id, SaleZoneAreaId, Description)
                VALUES (:id, 1, :description)
                """
            ),
            {"id": sale_zone_area_object_id, "description": str(sale_zone_area_object_id)},
        )

    def _service_percent(self, connection) -> Decimal:
        row = connection.execute(
            text("SELECT COALESCE(UsingServiceTax, 0) AS enabled, COALESCE(ServiceTxtTax, 0) AS percent FROM xconfig LIMIT 1")
        ).mappings().first()
        if not row or not int(row["enabled"] or 0):
            return Decimal("0")
        return Decimal(str(row["percent"] or "0"))

    def _resolve_user_id(self, connection, operator_code: str | None, operator_name: str | None, fallback: int) -> int:
        for value in (operator_code, operator_name):
            if not value:
                continue
            found = connection.execute(
                text(
                    """
                    SELECT Id
                    FROM users
                    WHERE CAST(Id AS CHAR) = :value OR Name = :value
                    LIMIT 1
                    """
                ),
                {"value": str(value)},
            ).scalar()
            if found is not None:
                return int(found)
        return int(fallback or 0)

    def _build_line(
        self,
        *,
        order: StoredOrder,
        item,
        sale_zone_area_object_id: int,
        order_number: int,
        sort_number: int,
        context: dict[str, int],
        user_id: int,
        created_at: datetime,
        connection,
    ) -> dict[str, object]:
        item_data = self._load_item_data(connection, item.product_code)
        quantity = _money6(item.quantity)
        retail_price = _money6(item.unit_price)
        total = _money6(item.line_total)
        tax_rate = _money6(item_data["tax_value"])
        income = _money6(total / (Decimal("1") + (tax_rate / Decimal("100")))) if tax_rate else total
        tax_amount = _money6(total - income)
        net_price = _money2(retail_price / (Decimal("1") + (tax_rate / Decimal("100")))) if tax_rate else retail_price
        return {
            "Session": context["session"],
            "Shift": context["shift"],
            "Terminal": self.terminal_id,
            "NumDocCX": self.terminal_id,
            "SaleZoneAreaObjectId": sale_zone_area_object_id,
            "SerieId": context["serie_id"],
            "Number": 1,
            "OrderNumber": order_number,
            "SessionDate": created_at,
            "CreationUserId": user_id,
            "CreationDate": created_at,
            "CloseUserId": 0,
            "CloseDate": ZERO_DATE,
            "SortNumber": sort_number,
            "SortLevel": 1,
            "EntityKeyId": "0",
            "ItemKeyId": item.product_code,
            "ItemGroupId": item_data["group_id"],
            "ItemDescription": item.description,
            "ItemType": item_data["item_type"],
            "Quantity": quantity,
            "RetailPrice": retail_price,
            "TaxId": item_data["tax_id"],
            "TaxValue": tax_rate,
            "Discount": "0",
            "DiscountValue": Decimal("0.000000"),
            "TotalIncome": income,
            "TotalTaxes": tax_amount,
            "TotalDiscounts": Decimal("0.000000"),
            "Total": total,
            "PaymentType": context["payment_type"],
            "Deleted": 0,
            "DeletedDate": None,
            "Bar": None,
            "DocumentTypeId": 0,
            "IdShop": context["id_shop"],
            "ReasonsCancellation": None,
            "Observation": item.notes or "",
            "IsOffer": 0,
            "SortKey": sort_number,
            "HoldingTaxValue": Decimal("0.000000"),
            "TotalHoldingTaxes": Decimal("0.000000"),
            "CurrencyId": context["currency_id"],
            "CurrencyRate": Decimal("1.000000"),
            "PaymentDivisionDiscount": Decimal("0.000000"),
            "ServiceTaxValue": Decimal("0.000000"),
            "ServiceTaxUserId": 0,
            "DocumentGuid": ZERO_GUID,
            "Guid": str(uuid4()),
            "ParentGuid": order.uuid,
            "NetPrice": net_price,
            "OriginWarehouse": context["warehouse_id"],
            "DestinationWarehouse": 0,
            "DiscountPercent1": None,
            "DiscountPercent2": None,
            "DiscountPercent3": None,
            "TotalNetAmount": income,
            "TotalTaxAmount": tax_amount,
            "TotalAmount": total,
            "TaxPointDate": ZERO_DATE,
            "HeaderDiscountAmount": Decimal("0.000000"),
            "Commission": Decimal("0.000000"),
            "StockFlow": 0,
            "StockBehavior": int(item_data["stock_behavior"]),
            "LastCostPrice": item_data["last_cost_price"],
            "AverageCostPrice": item_data["average_cost_price"],
            "TaxAmount": tax_amount,
            "SecondTaxAmount": Decimal("0.000000"),
            "SecondTaxId": 0,
            "SecondTaxValue": Decimal("0.000000"),
            "VolumeCount": Decimal("0.000000"),
            "Measure1": Decimal("0.000000"),
            "Measure2": Decimal("0.000000"),
            "Measure3": Decimal("0.000000"),
            "CloudSyncStamp": None,
        }

    def _load_item_data(self, connection, product_code: str) -> dict[str, object]:
        row = connection.execute(
            text(
                """
                SELECT i.GroupId, i.ItemType, i.Tax1, 0 AS StockBehavior,
                       i.AverageCostPrice, xt.Tax AS TaxValue
                FROM items i
                LEFT JOIN xconfigtaxes xt ON xt.Id = i.Tax1
                WHERE i.KeyId = :product_code
                LIMIT 1
                """
            ),
            {"product_code": product_code},
        ).mappings().first()
        if row is None:
            return {
                "group_id": 0,
                "item_type": 0,
                "tax_id": 1,
                "tax_value": Decimal("0"),
                "stock_behavior": 0,
                "last_cost_price": None,
                "average_cost_price": Decimal("0.000000"),
            }
        return {
            "group_id": int(row["GroupId"] or 0),
            "item_type": int(row["ItemType"] or 0),
            "tax_id": int(row["Tax1"] or 1),
            "tax_value": Decimal(str(row["TaxValue"] or "0")),
            "stock_behavior": int(row["StockBehavior"] or 0) if "StockBehavior" in row else 0,
            "last_cost_price": None,
            "average_cost_price": Decimal(str(row["AverageCostPrice"] or "0")),
        }

    @staticmethod
    def _parse_command_number(command_number: str) -> int:
        try:
            value = int(str(command_number).strip())
        except (TypeError, ValueError):
            raise ValueError("Mesa precisa ser numerica para entrar no XD.") from None
        if value <= 0:
            raise ValueError("Mesa precisa ser maior que zero para entrar no XD.")
        return value


def _naive_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.replace(tzinfo=None)


def _money6(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _money2(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _money3(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
