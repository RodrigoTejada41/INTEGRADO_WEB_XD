from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.sync_repository import SyncRepository


class DashboardService:
    def __init__(self, db: Session):
        self.repo = SyncRepository(db)

    def summary(
        self,
        *,
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> dict:
        base = self.repo.dashboard_counts(
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        base['chart_daily'] = self.repo.chart_by_day(
            30,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        base['latest_batches'] = self.repo.latest_batches(
            10,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        base['api_status'] = 'online'
        return base
