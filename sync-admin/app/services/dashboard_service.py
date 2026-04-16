from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.sync_repository import SyncRepository


class DashboardService:
    def __init__(self, db: Session):
        self.repo = SyncRepository(db)

    def summary(self) -> dict:
        base = self.repo.dashboard_counts()
        base['chart_daily'] = self.repo.chart_by_day(30)
        base['latest_batches'] = self.repo.latest_batches(10)
        base['api_status'] = 'online'
        return base
