import logging
import time
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.config.logging import configure_logging

from agent_local.config.settings import get_agent_settings
from agent_local.db.mariadb_client import MariaDBClient
from agent_local.sync.api_client import SyncApiClient
from agent_local.sync.checkpoint_store import CheckpointStore
from agent_local.sync.healthcheck import AgentHealthcheck
from agent_local.sync.sync_runner import SyncRunner


def main() -> None:
    settings = get_agent_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    mariadb_client = MariaDBClient(
        settings.mariadb_url,
        source_query=settings.source_query,
    )
    api_client = SyncApiClient(
        base_url=settings.api_base_url,
        empresa_id=settings.empresa_id,
        api_key=settings.api_key,
        timeout_seconds=settings.timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )
    checkpoint_store = CheckpointStore(settings.checkpoint_file)

    key_file_path = Path(settings.api_key_file) if settings.api_key_file else None
    audit_file_path = Path(settings.audit_file) if settings.audit_file else None

    def resolve_api_key() -> str:
        if key_file_path and key_file_path.exists():
            value = key_file_path.read_text(encoding="utf-8").strip()
            if value:
                return value
        return settings.api_key

    def append_audit(level: str, event: str, context: dict) -> None:
        if not audit_file_path:
            return
        audit_file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": event,
            "empresa_id": settings.empresa_id,
            "context": context,
        }
        with audit_file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=True) + "\n")

    runner = SyncRunner(
        empresa_id=settings.empresa_id,
        mariadb_client=mariadb_client,
        api_client=api_client,
        checkpoint_store=checkpoint_store,
        batch_size=settings.batch_size,
        api_key_provider=resolve_api_key,
    )
    healthcheck = AgentHealthcheck(
        mariadb_client=mariadb_client,
        api_base_url=settings.api_base_url,
        timeout_seconds=settings.timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )

    interval_seconds = settings.sync_interval_minutes * 60
    logger.info(
        "agent_started",
        extra={
            "empresa_id": settings.empresa_id,
            "interval_minutes": settings.sync_interval_minutes,
        },
    )
    while True:
        try:
            preflight = healthcheck.run_preflight()
            if not preflight["ok"]:
                logger.error(
                    "agent_preflight_failed",
                    extra={
                        "empresa_id": settings.empresa_id,
                        "mariadb_ok": preflight["mariadb_ok"],
                        "api_ok": preflight["api_ok"],
                        "errors": preflight["errors"],
                    },
                )
                append_audit(
                    level="error",
                    event="agent_preflight_failed",
                    context={
                        "mariadb_ok": preflight["mariadb_ok"],
                        "api_ok": preflight["api_ok"],
                        "errors": preflight["errors"],
                    },
                )
            else:
                result = runner.run_once()
                append_audit(level="info", event="agent_sync_cycle", context=result)
        except Exception:
            logger.exception("agent_sync_error")
            append_audit(level="error", event="agent_sync_error", context={})
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
