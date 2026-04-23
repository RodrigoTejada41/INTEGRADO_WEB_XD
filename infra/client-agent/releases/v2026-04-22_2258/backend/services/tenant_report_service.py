from __future__ import annotations

from datetime import date

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

    def get_overview(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> dict[str, object]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        return self.venda_repository.report_overview(
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )

    def get_daily_sales(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> list[dict[str, object]]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        return self.venda_repository.report_daily_sales(
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
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
    ) -> list[dict[str, object]]:
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        return self.venda_repository.report_top_products(
            empresa_id=empresa_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
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
    ):
        self.ensure_tenant_exists(empresa_id)
        self.validate_date_range(start_date, end_date)
        return self.venda_repository.report_recent_sales(
            empresa_id=empresa_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
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
