from __future__ import annotations

from pathlib import Path

from agent_local.orders.printer import LocalOrderPrinter
from agent_local.orders.repository import LocalOrderRepository, StoredOrder, StoredOrderSession
from agent_local.orders.schemas import LocalOrderCancelRequest, LocalOrderCloseRequest, LocalOrderCreate, LocalOrderItemCreate, LocalOrderItemUpdate


class LocalOrderService:
    def __init__(self, repository: LocalOrderRepository, empresa_id: str):
        self.repository = repository
        self.empresa_id = empresa_id

    def create_order(self, payload: LocalOrderCreate) -> StoredOrder:
        return self.repository.create(self.empresa_id, payload)

    def list_orders(self, table_reference: str | None = None) -> list[StoredOrder]:
        return self.repository.list(self.empresa_id, table_reference=table_reference)

    def list_operators(self) -> list[dict[str, str]]:
        return self.repository.list_operators()

    def authenticate_operator(self, code: str, password: str) -> StoredOrderSession:
        return self.repository.authenticate_operator(code, password)

    def get_session(self, token: str) -> StoredOrderSession | None:
        return self.repository.get_session(token)

    def list_product_families(self) -> list[str]:
        return self.repository.list_product_families()

    def list_products(self, family: str | None = None, query: str | None = None) -> list[dict[str, str]]:
        return self.repository.list_products(family=family, query=query)

    def add_item(self, order_uuid: str, payload: LocalOrderItemCreate) -> StoredOrder:
        return self.repository.add_item(empresa_id=self.empresa_id, order_uuid=order_uuid, payload=payload)

    def update_item(self, order_uuid: str, item_id: int, payload: LocalOrderItemUpdate) -> StoredOrder:
        return self.repository.update_item(
            empresa_id=self.empresa_id,
            order_uuid=order_uuid,
            item_id=item_id,
            payload=payload,
        )

    def remove_item(self, order_uuid: str, item_id: int) -> StoredOrder:
        return self.repository.remove_item(empresa_id=self.empresa_id, order_uuid=order_uuid, item_id=item_id)

    def clear_items(self, order_uuid: str) -> StoredOrder:
        return self.repository.clear_items(empresa_id=self.empresa_id, order_uuid=order_uuid)

    def close_order(self, order_uuid: str, payload: LocalOrderCloseRequest) -> StoredOrder:
        return self.repository.close_order(empresa_id=self.empresa_id, order_uuid=order_uuid, payload=payload)

    def cancel_order(self, order_uuid: str, payload: LocalOrderCancelRequest) -> StoredOrder:
        return self.repository.cancel_order(empresa_id=self.empresa_id, order_uuid=order_uuid, reason=payload.reason)

    def print_order(self, order_uuid: str, *, jobs_dir: str | Path, printer_name: str | None, width: int):
        order = self.repository.get_by_uuid(empresa_id=self.empresa_id, order_uuid=order_uuid)
        return LocalOrderPrinter(jobs_dir=jobs_dir, printer_name=printer_name, width=width).create_job(order)
