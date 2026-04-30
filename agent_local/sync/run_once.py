from pathlib import Path

from backend.config.logging import configure_logging

from agent_local.config.settings import get_agent_settings
from agent_local.db.mariadb_client import MariaDBClient
from agent_local.sync.api_client import SyncApiClient
from agent_local.sync.checkpoint_store import CheckpointStore
from agent_local.sync.healthcheck import AgentHealthcheck
from agent_local.sync.sync_runner import SyncRunner


def main() -> int:
    settings = get_agent_settings()
    configure_logging(settings.log_level)
    key_file_path = Path(settings.api_key_file) if settings.api_key_file else None

    def resolve_api_key() -> str | None:
        if key_file_path and key_file_path.exists():
            value = key_file_path.read_text(encoding="utf-8").strip()
            if value:
                return value
        return (settings.api_key or "").strip() or None

    if not settings.empresa_id:
        raise SystemExit("AGENT_EMPRESA_ID ausente.")
    if not resolve_api_key():
        raise SystemExit("API key ausente. Configure AGENT_API_KEY ou AGENT_API_KEY_FILE.")

    mariadb_client = MariaDBClient(settings.mariadb_url, source_query=settings.source_query)
    healthcheck = AgentHealthcheck(
        mariadb_client=mariadb_client,
        api_base_url=settings.api_base_url,
        timeout_seconds=settings.timeout_seconds,
        verify_ssl=settings.verify_ssl,
    )
    preflight = healthcheck.run_preflight()
    if not preflight["ok"]:
        raise SystemExit(f"Preflight falhou: {preflight}")

    runner = SyncRunner(
        empresa_id=settings.empresa_id,
        mariadb_client=mariadb_client,
        api_client=SyncApiClient(
            base_url=settings.api_base_url,
            empresa_id=settings.empresa_id,
            api_key=(settings.api_key or "").strip(),
            timeout_seconds=settings.timeout_seconds,
            verify_ssl=settings.verify_ssl,
        ),
        checkpoint_store=CheckpointStore(settings.checkpoint_file),
        batch_size=settings.batch_size,
        api_key_provider=resolve_api_key,
    )
    print(runner.run_once())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
