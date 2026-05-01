import logging
from datetime import UTC, datetime
from typing import Callable

from agent_local.db.mariadb_client import MariaDBClient
from agent_local.db.xd_sales_mapper import OPTIONAL_CANONICAL_FIELDS
from agent_local.sync.api_client import SyncApiClient
from agent_local.sync.checkpoint_store import CheckpointStore

logger = logging.getLogger(__name__)


class SyncRunner:
    def __init__(
        self,
        empresa_id: str,
        mariadb_client: MariaDBClient,
        api_client: SyncApiClient,
        checkpoint_store: CheckpointStore,
        batch_size: int,
        api_key_provider: Callable[[], str | None] | None = None,
    ):
        self.empresa_id = empresa_id
        self.mariadb_client = mariadb_client
        self.api_client = api_client
        self.checkpoint_store = checkpoint_store
        self.batch_size = batch_size
        self.api_key_provider = api_key_provider

    def run_once(self) -> dict:
        checkpoint_key = f"{self.empresa_id}:vendas"
        since = self.checkpoint_store.get(checkpoint_key)
        records = self.mariadb_client.fetch_changed_vendas(
            empresa_id=self.empresa_id,
            since=since,
            limit=self.batch_size,
        )

        if not records:
            logger.info("no_records_to_sync", extra={"empresa_id": self.empresa_id})
            self._send_status(
                status="success",
                processed_count=0,
                reason="no_records",
            )
            return {"status": "ok", "processed_count": 0}

        payload = {
            "empresa_id": self.empresa_id,
            "records": [self._build_payload_record(record) for record in records],
        }
        source_metadata = self.mariadb_client.fetch_source_metadata(self.empresa_id)
        if source_metadata:
            payload["source_metadata"] = source_metadata
        api_key = self.api_key_provider() if self.api_key_provider else None
        response = self.api_client.send_sync_batch(payload, api_key=api_key)

        max_update = max(datetime.fromisoformat(record["data_atualizacao"]) for record in records)
        self.checkpoint_store.set(checkpoint_key, max_update)
        processed_count = int(response.get("processed_count", 0) or 0)
        self._send_status(
            status="success",
            processed_count=processed_count,
            reason="sync_batch",
        )

        logger.info(
            "sync_success",
            extra={
                "empresa_id": self.empresa_id,
                "sent_count": len(records),
                "processed_count": processed_count,
            },
        )
        return response

    def _send_status(self, *, status: str, processed_count: int, reason: str) -> None:
        api_key = self.api_key_provider() if self.api_key_provider else None
        try:
            self.api_client.send_sync_status(
                last_sync_at=datetime.now(UTC).isoformat(),
                status=status,
                processed_count=processed_count,
                reason=reason,
                api_key=api_key,
            )
        except Exception as exc:
            logger.warning(
                "sync_status_update_failed",
                extra={"empresa_id": self.empresa_id, "reason": reason, "error": str(exc)},
            )

    def _build_payload_record(self, record: dict) -> dict:
        payload_record = {
            "uuid": record["uuid"],
            "produto": record["produto"],
            "valor": record["valor"],
            "data": record["data"],
            "data_atualizacao": record["data_atualizacao"],
        }
        for field in OPTIONAL_CANONICAL_FIELDS:
            value = record.get(field)
            if value is not None and str(value).strip():
                payload_record[field] = value if isinstance(value, bool) else str(value).strip()
        return payload_record
