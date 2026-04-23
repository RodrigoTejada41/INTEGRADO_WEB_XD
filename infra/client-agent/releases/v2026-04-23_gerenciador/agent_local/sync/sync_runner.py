import logging
from datetime import datetime
from typing import Callable

from agent_local.db.mariadb_client import MariaDBClient
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
            return {"status": "ok", "processed_count": 0}

        payload = {
            "empresa_id": self.empresa_id,
            "records": [
                {
                    "uuid": record["uuid"],
                    "produto": record["produto"],
                    "valor": record["valor"],
                    "data": record["data"],
                    "data_atualizacao": record["data_atualizacao"],
                }
                for record in records
            ],
        }
        api_key = self.api_key_provider() if self.api_key_provider else None
        response = self.api_client.send_sync_batch(payload, api_key=api_key)

        max_update = max(datetime.fromisoformat(record["data_atualizacao"]) for record in records)
        self.checkpoint_store.set(checkpoint_key, max_update)

        logger.info(
            "sync_success",
            extra={
                "empresa_id": self.empresa_id,
                "sent_count": len(records),
                "processed_count": response.get("processed_count", 0),
            },
        )
        return response
