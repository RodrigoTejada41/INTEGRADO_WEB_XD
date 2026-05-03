from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LocalOrderItemCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=3)
    unit_price: Decimal = Field(ge=Decimal("0"), max_digits=14, decimal_places=4)
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("product_code", "description", "notes")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned


class LocalOrderItemUpdate(BaseModel):
    quantity: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=14, decimal_places=3)
    unit_price: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=14, decimal_places=4)
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("notes")
    @classmethod
    def strip_optional_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderPaymentCreate(BaseModel):
    payment_method: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)

    @field_validator("payment_method")
    @classmethod
    def strip_payment_method(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Forma de pagamento obrigatoria.")
        return cleaned


class LocalOrderCloseRequest(BaseModel):
    payment_method: str | None = Field(default=None, max_length=80)
    amount_paid: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=14, decimal_places=2)
    payments: list[LocalOrderPaymentCreate] | None = Field(default=None, min_length=1, max_length=10)

    @field_validator("payment_method")
    @classmethod
    def strip_optional_payment_method(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderCreate(BaseModel):
    command_number: str | None = Field(default=None, max_length=40)
    table_reference: str | None = Field(default=None, max_length=40)
    operator_code: str | None = Field(default=None, max_length=80)
    operator_name: str | None = Field(default=None, max_length=160)
    customer_name: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=500)
    items: list[LocalOrderItemCreate] = Field(min_length=1, max_length=200)

    @field_validator("command_number", "table_reference", "operator_code", "operator_name", "customer_name", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderItemView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    notes: str | None


class LocalOrderPaymentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_method: str
    amount: Decimal


class LocalOrderView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    empresa_id: str
    command_number: str
    table_reference: str | None
    operator_code: str | None
    operator_name: str | None
    customer_name: str | None
    status: str
    sync_status: str
    total_amount: Decimal
    payment_method: str | None = None
    amount_paid: Decimal | None = None
    closed_at: datetime | None = None
    cancel_reason: str | None = None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[LocalOrderItemView]
    payments: list[LocalOrderPaymentView] = Field(default_factory=list)


class LocalOrderPrintResponse(BaseModel):
    order_uuid: str
    status: str
    printer_name: str | None = None
    job_path: str
    message: str | None = None


class LocalOrderListResponse(BaseModel):
    total: int
    orders: list[LocalOrderView]


class LocalOperatorView(BaseModel):
    code: str
    name: str


class LocalOperatorListResponse(BaseModel):
    operators: list[LocalOperatorView]


class LocalProductFamilyListResponse(BaseModel):
    families: list[str]


class LocalProductView(BaseModel):
    product_code: str
    description: str
    family: str
    unit_price: Decimal


class LocalProductListResponse(BaseModel):
    products: list[LocalProductView]
