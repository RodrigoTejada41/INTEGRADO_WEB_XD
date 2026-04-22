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

    key_file_path = Path(settings.api_key_file) if settings.api_key_file else None
    audit_file_path = Path(settings.audit_file) if settings.audit_file else None
    runtime_empresa_id = settings.empresa_id
    runtime_api_key = (settings.api_key or "").strip()

    def resolve_api_key() -> str | None:
        if key_file_path and key_file_path.exists():
            value = key_file_path.read_text(encoding="utf-8").strip()
            if value:
                return value
        return runtime_api_key or None

    def append_audit(level: str, event: str, context: dict) -> None:
        if not audit_file_path:
            return
        audit_file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": event,
            "empresa_id": runtime_empresa_id,
            "context": context,
        }
        with audit_file_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=True) + "\n")

    preflight_api_client = SyncApiClient(
        base_url=settings.api_base_url,
        empresa_id=runtime_empresa_id or "__pending__",
        api_key=runtime_api_key,
        timeout_seconds=settings.timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )

    if not resolve_api_key() and settings.pairing_code:
        activation = preflight_api_client.activate_pairing_code(
            pairing_code=settings.pairing_code,
            device_label=settings.device_label,
        )
        activated_empresa_id = str(activation["empresa_id"])
        activated_api_key = str(activation["api_key"])
        if runtime_empresa_id and runtime_empresa_id != activated_empresa_id:
            raise RuntimeError("empresa_id configurado difere do empresa_id vinculado no codigo.")
        runtime_empresa_id = activated_empresa_id
        runtime_api_key = activated_api_key
        if key_file_path:
            key_file_path.parent.mkdir(parents=True, exist_ok=True)
            key_file_path.write_text(activated_api_key, encoding="utf-8")
        append_audit(
            level="info",
            event="agent_pairing_activated",
            context={"device_label": settings.device_label},
        )

    if not runtime_empresa_id:
        raise RuntimeError("AGENT_EMPRESA_ID ausente e nenhum codigo de vinculacao valido foi informado.")

    mariadb_client = MariaDBClient(
        settings.mariadb_url,
        source_query=settings.source_query,
    )
    api_client = SyncApiClient(
        base_url=settings.api_base_url,
        empresa_id=runtime_empresa_id,
        api_key=runtime_api_key,
        timeout_seconds=settings.timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )
    checkpoint_store = CheckpointStore(settings.checkpoint_file)

    def require_api_key() -> str:
        current = resolve_api_key()
        if not current:
            raise RuntimeError("API key ausente. Configure AGENT_API_KEY ou AGENT_PAIRING_CODE.")
        return current

    runner = SyncRunner(
        empresa_id=runtime_empresa_id,
        mariadb_client=mariadb_client,
        api_client=api_client,
        checkpoint_store=checkpoint_store,
        batch_size=settings.batch_size,
        api_key_provider=require_api_key,
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
            "empresa_id": runtime_empresa_id,
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
                        "empresa_id": runtime_empresa_id,
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
