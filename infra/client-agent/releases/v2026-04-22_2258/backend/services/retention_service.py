import logging
from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import sessionmaker

from backend.repositories.venda_repository import VendaRepository
from backend.utils.metrics import metrics_registry

logger = logging.getLogger(__name__)


class RetentionService:
    def __init__(
        self,
        session_factory: sessionmaker,
        retention_months: int,
        retention_mode: str,
    ):
        self.session_factory = session_factory
        self.retention_months = retention_months
        self.retention_mode = retention_mode

    def run(self) -> int:
        cutoff_date = (datetime.now(UTC) - relativedelta(months=self.retention_months)).date()
        with self.session_factory() as session:
            repository = VendaRepository(session)
            processed = repository.retain_recent_data(
                cutoff_date=cutoff_date,
                mode=self.retention_mode,
            )
            session.commit()

        logger.info(
            "retention_execution",
            extra={
                "retention_mode": self.retention_mode,
                "retention_months": self.retention_months,
                "processed_rows": processed,
            },
        )
        metrics_registry.record_retention(processed)
        return processed
