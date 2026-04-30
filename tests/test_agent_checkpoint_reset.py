from datetime import UTC, datetime
from pathlib import Path

from agent_local.sync.checkpoint_store import CheckpointStore
from agent_local.sync.reset_checkpoint import parse_checkpoint_datetime


def test_checkpoint_store_resets_tenant_vendas_checkpoint() -> None:
    output_dir = Path("output/test_agent_checkpoint_reset")
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = output_dir / "checkpoints.json"
    store = CheckpointStore(str(checkpoint_file))
    key = "12345678000199:vendas"

    store.set(key, datetime(2026, 4, 29, 10, 0, tzinfo=UTC))
    reset_value = store.reset(key)

    assert reset_value == datetime(1970, 1, 1, tzinfo=UTC)
    assert store.get(key) == datetime(1970, 1, 1, tzinfo=UTC)


def test_parse_checkpoint_datetime_assumes_utc_when_timezone_is_missing() -> None:
    parsed = parse_checkpoint_datetime("2026-04-01T00:00:00")

    assert parsed == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)
