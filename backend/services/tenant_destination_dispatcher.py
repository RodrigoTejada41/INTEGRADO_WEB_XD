from __future__ import annotations

import logging
from datetime import UTC, datetime
from sqlalchemy.orm import sessionmaker

from backend.connectors.destination_connectors import get_default_destination_connector_registry
from backend.models.tenant_destination_config import TenantDestinationConfig
from backend.repositories.tenant_config_repository import TenantConfigRepository
from backend.utils.crypto import decrypt_json

logger = logging.getLogger(__name__)


class TenantDestinationDispatcher:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        self.connector_registry = get_default_destination_connector_registry()

    def dispatch_records(self, empresa_id: str, records: list[dict]) -> int:
        if not records:
            return 0

        delivered_total = 0
        with self.session_factory() as session:
            repository = TenantConfigRepository(session, TenantDestinationConfig)
            configs = repository.list_active_by_empresa_id(empresa_id)
            if not configs:
                return 0

            for config in configs:
                settings = decrypt_json(config.settings_json)
                connector = self.connector_registry.get(config.connector_type)
                try:
                    result = connector.deliver_records(
                        settings=settings,
                        empresa_id=empresa_id,
                        records=records,
                    )
                    config.last_run_at = datetime.now(UTC)
                    config.last_status = "ok"
                    config.last_error = None
                    delivered_total += result.delivered_count
                except Exception as exc:
                    config.last_run_at = datetime.now(UTC)
                    config.last_status = "failed"
                    config.last_error = str(exc)
                    session.commit()
                    logger.exception(
                        "tenant_destination_delivery_failed",
                        extra={
                            "empresa_id": empresa_id,
                            "destination_config_id": config.id,
                            "connector_type": config.connector_type,
                        },
                    )
                    raise

            session.commit()

        logger.info(
            "tenant_destination_delivery_completed",
            extra={"empresa_id": empresa_id, "delivered_total": delivered_total},
        )
        return delivered_total
