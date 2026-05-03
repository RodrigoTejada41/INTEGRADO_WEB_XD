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


class LocalOrderOperationRequest(BaseModel):
    order_uuid: str | None = Field(default=None, max_length=80)
    command_number: str | None = Field(default=None, max_length=40)
    item_id: int | None = Field(default=None, gt=0)
    reason: str | None = Field(default=None, min_length=1, max_length=300)
    details: dict[str, str | int | Decimal | None] | None = None

    @field_validator("order_uuid", "command_number", "reason")
    @classmethod
    def strip_operation_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderTransferRequest(BaseModel):
    transfer_type: str = Field(pattern="^(item|command|table)$")
    source_order_uuid: str | None = Field(default=None, max_length=80)
    source_command_number: str | None = Field(default=None, max_length=40)
    item_id: int | None = Field(default=None, gt=0)
    destination_command_number: str | None = Field(default=None, max_length=40)
    destination_table_reference: str | None = Field(default=None, max_length=40)
    reason: str = Field(min_length=1, max_length=300)

    @field_validator(
        "source_order_uuid",
        "source_command_number",
        "destination_command_number",
        "destination_table_reference",
        "reason",
    )
    @classmethod
    def strip_transfer_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderPartialPaymentRequest(BaseModel):
    order_uuid: str | None = Field(default=None, max_length=80)
    command_number: str | None = Field(default=None, max_length=40)
    payment_method: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    selected_item_ids: list[int] | None = Field(default=None, max_length=100)

    @field_validator("order_uuid", "command_number", "payment_method")
    @classmethod
    def strip_partial_payment_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderDiscountRequest(BaseModel):
    order_uuid: str | None = Field(default=None, max_length=80)
    command_number: str | None = Field(default=None, max_length=40)
    discount_type: str = Field(pattern="^(fixed|percent)$")
    value: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=2)
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("order_uuid", "command_number", "reason")
    @classmethod
    def strip_discount_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalCommandaSettings(BaseModel):
    ip_servidor: str | None = Field(default=None, max_length=120)
    porta_servidor: int | None = Field(default=None, ge=1, le=65535)
    licenca: str | None = Field(default=None, max_length=160)
    ssid_wifi: str | None = Field(default=None, max_length=255)
    impressora_bluetooth: str | None = Field(default=None, max_length=160)
    dpi_impressora: int | None = Field(default=203, ge=72, le=600)
    largura_impressora: int | None = Field(default=58, ge=20, le=120)
    caracteres_por_linha: int | None = Field(default=32, ge=16, le=80)
    tema_interface: str | None = Field(default="padrao", max_length=80)
    usuario_logado: str | None = Field(default=None, max_length=80)
    versao_app: str | None = Field(default=None, max_length=40)
    codigo_versao: str | None = Field(default=None, max_length=80)

    @field_validator(
        "ip_servidor",
        "licenca",
        "ssid_wifi",
        "impressora_bluetooth",
        "tema_interface",
        "usuario_logado",
        "versao_app",
        "codigo_versao",
    )
    @classmethod
    def strip_settings_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LocalOrderCreate(BaseModel):
    command_number: str | None = Field(default=None, max_length=40)
    people_count: int | None = Field(default=None, ge=1, le=999)
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
    people_count: int | None = None
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


class LocalOrderLoginRequest(BaseModel):
    operator_code: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("operator_code")
    @classmethod
    def strip_operator_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Usuario obrigatorio.")
        return cleaned


class LocalOrderLoginResponse(BaseModel):
    session_token: str
    operator: LocalOperatorView


class LocalOperatorContextResponse(BaseModel):
    operator: LocalOperatorView
    permissions: dict[str, bool]


class LocalOrderActionResponse(BaseModel):
    status: str
    message: str
    order: LocalOrderView | None = None
    payload: dict[str, object] | None = None


class LocalCommandaAppInfoResponse(BaseModel):
    app_name: str
    version_name: str
    version_code: str


class LocalCommandaSettingsResponse(BaseModel):
    settings: LocalCommandaSettings


class LocalProductFamilyListResponse(BaseModel):
    families: list[str]


class LocalProductView(BaseModel):
    product_code: str
    description: str
    family: str
    unit_price: Decimal


class LocalProductListResponse(BaseModel):
    products: list[LocalProductView]
