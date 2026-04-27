from __future__ import annotations

from datetime import date, time

from fastapi import HTTPException, status

from backend.repositories.tenant_repository import TenantRepository
from backend.repositories.venda_repository import VendaRepository


class TenantReportService:
    def __init__(self, tenant_repository: TenantRepository, venda_repository: VendaRepository):
        self.tenant_repository = tenant_repository
        self.venda_repository = venda_repository

    def ensure_tenant_exists(self, empresa_id: str) -> None:
        tenant = self.tenant_repository.get_by_empresa_id(empresa_id)
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant nao encontrado.")

    @staticmethod
    def validate_date_range(start_date: date | None, end_date: date | None) -> None:
        if start_date and end_date and end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date deve ser maior ou igual a start_date.",
            )

    @staticmethod
    def validate_time_range(start_time: time | None, end_time: time | None) -> None:
        if start_time and end_time and end_time < start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time deve ser maior ou igual a start_time.",
            )

    def get_overview(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
    ) -> dict[str, object]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        self.validate_time_range(start_time, end_time)
        return self.venda_repository.report_overview(
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
            start_time=start_time,
            end_time=end_time,
        )

    def get_daily_sales(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
    ) -> list[dict[str, object]]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        self.validate_time_range(start_time, end_time)
        return self.venda_repository.report_daily_sales(
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
            start_time=start_time,
            end_time=end_time,
        )

    def get_top_products(
        self,
        *,
        empresa_id: str,
        limit: int,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
    ) -> list[dict[str, object]]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        self.validate_time_range(start_time, end_time)
        return self.venda_repository.report_top_products(
            empresa_id=empresa_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
            start_time=start_time,
            end_time=end_time,
        )

    def get_sales_breakdown(
        self,
        *,
        empresa_id: str,
        group_by: str,
        limit: int,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
    ) -> list[dict[str, object]]:
        if group_by not in {"tipo_venda", "forma_pagamento", "familia_produto"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_by invalido para relatorio.",
            )
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        self.validate_time_range(start_time, end_time)
        return self.venda_repository.report_sales_breakdown(
            empresa_id=empresa_id,
            group_by=group_by,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
            start_time=start_time,
            end_time=end_time,
        )

    def get_recent_sales(
        self,
        *,
        empresa_id: str,
        limit: int,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
    ):
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        self.validate_time_range(start_time, end_time)
        return self.venda_repository.report_recent_sales(
            empresa_id=empresa_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
            start_time=start_time,
            end_time=end_time,
        )

    def get_branch_codes(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        terminal_code: str | None = None,
    ) -> list[str]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        return self.venda_repository.report_branch_codes(
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            terminal_code=terminal_code,
        )
