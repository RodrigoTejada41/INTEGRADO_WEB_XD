from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TenantReportOverviewResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    total_records: int
    total_sales_value: Decimal
    total_gross_value: Decimal = Decimal("0")
    total_discount_value: Decimal = Decimal("0")
    total_surcharge_value: Decimal = Decimal("0")
    total_quantity: Decimal = Decimal("0")
    distinct_products: int
    distinct_branches: int
    distinct_terminals: int
    first_sale_date: date | None = None
    last_sale_date: date | None = None


class TenantDailySalesPointResponse(BaseModel):
    day: date
    total_records: int
    total_sales_value: Decimal


class TenantTopProductResponse(BaseModel):
    codigo_produto_local: str | None = None
    produto: str
    familia_produto: str | None = None
    categoria_produto: str | None = None
    total_records: int
    quantity_sold: Decimal = Decimal("0")
    average_unit_value: Decimal = Decimal("0")
    gross_value: Decimal = Decimal("0")
    discount_value: Decimal = Decimal("0")
    surcharge_value: Decimal = Decimal("0")
    total_sales_value: Decimal


class TenantSalesBreakdownItemResponse(BaseModel):
    label: str
    total_records: int
    quantity_sold: Decimal = Decimal("0")
    gross_value: Decimal = Decimal("0")
    discount_value: Decimal = Decimal("0")
    surcharge_value: Decimal = Decimal("0")
    total_sales_value: Decimal


class TenantRecentSaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    branch_code: str | None = None
    terminal_code: str | None = None
    tipo_venda: str | None = None
    forma_pagamento: str | None = None
    bandeira_cartao: str | None = None
    familia_produto: str | None = None
    categoria_produto: str | None = None
    codigo_produto_local: str | None = None
    unidade: str | None = None
    operador: str | None = None
    cliente: str | None = None
    status_venda: str | None = None
    cancelada: bool = False
    produto: str
    quantidade: Decimal = Decimal("1")
    valor_unitario: Decimal | None = None
    valor_bruto: Decimal | None = None
    desconto: Decimal = Decimal("0")
    acrescimo: Decimal = Decimal("0")
    valor_liquido: Decimal | None = None
    valor: Decimal
    data: date
    data_atualizacao: datetime


class TenantDailySalesResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    items: list[TenantDailySalesPointResponse] = Field(default_factory=list)


class TenantTopProductsResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    limit: int
    items: list[TenantTopProductResponse] = Field(default_factory=list)


class TenantSalesBreakdownResponse(BaseModel):
    empresa_id: str
    group_by: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    limit: int
    items: list[TenantSalesBreakdownItemResponse] = Field(default_factory=list)


class TenantRecentSalesResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    limit: int
    items: list[TenantRecentSaleResponse] = Field(default_factory=list)


class TenantReportBranchesResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    terminal_code: str | None = None
    items: list[str] = Field(default_factory=list)


class TenantReportProductOptionResponse(BaseModel):
    produto: str
    codigo_produto_local: str | None = None


class TenantReportFilterOptionsResponse(BaseModel):
    empresa_id: str
    products: list[TenantReportProductOptionResponse] = Field(default_factory=list)
    product_codes: list[str] = Field(default_factory=list)
    families: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    payment_methods: list[str] = Field(default_factory=list)
    card_brands: list[str] = Field(default_factory=list)
    customers: list[str] = Field(default_factory=list)
    operators: list[str] = Field(default_factory=list)
    terminals: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
