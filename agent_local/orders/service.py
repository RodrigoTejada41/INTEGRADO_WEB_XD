from __future__ import annotations

from pathlib import Path

from agent_local.orders.printer import LocalOrderPrinter, LocalPrintJob
from agent_local.orders.repository import LocalOrderRepository, StoredOrder, StoredOrderSession
from agent_local.orders.schemas import (
    LocalOrderCancelRequest,
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

    def list_permissions(self, operator_code: str) -> dict[str, bool]:
        return self.repository.list_permissions(operator_code)

    def get_settings(self) -> LocalCommandaSettings:
        return self.repository.get_settings()

    def save_settings(self, payload: LocalCommandaSettings) -> LocalCommandaSettings:
        return self.repository.save_settings(payload)

    def list_group_printers(self) -> list[dict[str, object]]:
        return self.repository.list_group_printers()

    def save_group_printers(self, mappings: list[dict[str, object]]) -> list[dict[str, object]]:
        return self.repository.save_group_printers(mappings)

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

    def close_order(
        self,
        order_uuid: str,
        payload: LocalOrderCloseRequest,
        session: StoredOrderSession,
    ) -> StoredOrder:
        return self.repository.close_order(
            empresa_id=self.empresa_id,
            order_uuid=order_uuid,
            payload=payload,
            session=session,
        )

    def cancel_order(self, order_uuid: str, payload: LocalOrderCancelRequest) -> StoredOrder:
        return self.repository.cancel_order(empresa_id=self.empresa_id, order_uuid=order_uuid, reason=payload.reason)

    def order_summary(self, *, order_uuid: str | None = None, command_number: str | None = None) -> dict[str, object]:
        return self.repository.order_financial_summary(
            empresa_id=self.empresa_id,
            order_uuid=order_uuid,
            command_number=command_number,
        )

    def void_order_or_item(self, payload: LocalOrderOperationRequest, session: StoredOrderSession) -> StoredOrder:
        return self.repository.void_order_or_item(empresa_id=self.empresa_id, session=session, payload=payload)

    def transfer_order(self, payload: LocalOrderTransferRequest, session: StoredOrderSession) -> StoredOrder:
        return self.repository.transfer_order(empresa_id=self.empresa_id, session=session, payload=payload)

    def record_partial_payment(self, payload: LocalOrderPartialPaymentRequest, session: StoredOrderSession) -> dict[str, object]:
        return self.repository.record_partial_payment(empresa_id=self.empresa_id, session=session, payload=payload)

    def apply_discount(self, payload: LocalOrderDiscountRequest, session: StoredOrderSession) -> dict[str, object]:
        return self.repository.apply_discount(empresa_id=self.empresa_id, session=session, payload=payload)

    def list_messages(self, operator_code: str) -> list[dict[str, object]]:
        return self.repository.list_messages(operator_code)

    def list_outbox(self) -> list[dict[str, object]]:
        return self.repository.list_outbox()

    def print_order(self, order_uuid: str, *, jobs_dir: str | Path, printer_name: str | None, width: int):
        order = self.repository.get_by_uuid(empresa_id=self.empresa_id, order_uuid=order_uuid)
        return LocalOrderPrinter(jobs_dir=jobs_dir, printer_name=printer_name, width=width).create_job(order)

    def print_order_by_group(
        self,
        order: StoredOrder,
        *,
        jobs_dir: str | Path,
        width: int,
        spool_enabled: bool = True,
    ) -> list[LocalPrintJob]:
        jobs: list[LocalPrintJob] = []
        for group in self.repository.order_print_groups(order=order):
            job = LocalOrderPrinter(
                jobs_dir=jobs_dir,
                printer_name=group.printer_name,
                width=width,
                printer_id=group.printer_id,
                terminal_id=group.terminal_id,
                copies=group.copies,
                spool_enabled=spool_enabled,
            ).create_group_job(order, family=group.family, items=group.items)
            jobs.append(job)
        return jobs
