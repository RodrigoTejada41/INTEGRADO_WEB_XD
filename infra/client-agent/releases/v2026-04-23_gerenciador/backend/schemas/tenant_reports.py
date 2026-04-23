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
    total_records: int
    total_sales_value: Decimal
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
    produto: str
    total_records: int
    total_sales_value: Decimal


class TenantRecentSaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: str
    branch_code: str | None = None
    terminal_code: str | None = None
    produto: str
    valor: Decimal
    data: date
    data_atualizacao: datetime


class TenantDailySalesResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    items: list[TenantDailySalesPointResponse] = Field(default_factory=list)


class TenantTopProductsResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    limit: int
    items: list[TenantTopProductResponse] = Field(default_factory=list)


class TenantRecentSalesResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    branch_code: str | None = None
    terminal_code: str | None = None
    limit: int
    items: list[TenantRecentSaleResponse] = Field(default_factory=list)


class TenantReportBranchesResponse(BaseModel):
    empresa_id: str
    start_date: date | None = None
    end_date: date | None = None
    terminal_code: str | None = None
    items: list[str] = Field(default_factory=list)
