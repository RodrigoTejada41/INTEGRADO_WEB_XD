import argparse
from datetime import UTC, datetime

from agent_local.config.settings import get_agent_settings
from agent_local.sync.checkpoint_store import CheckpointStore


def parse_checkpoint_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reset local agent sync checkpoint safely.")
    parser.add_argument("--empresa-id", help="Tenant/CNPJ whose vendas checkpoint will be reset.")
    parser.add_argument("--entity", default="vendas", choices=["vendas"], help="Checkpoint entity.")
    parser.add_argument("--since", help="ISO datetime to reprocess from. Default: 1970-01-01T00:00:00+00:00.")
    parser.add_argument("--checkpoint-file", help="Checkpoint JSON file. Default comes from agent settings.")
    parser.add_argument("--confirm", action="store_true", help="Required to write the checkpoint.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = None
    if not args.empresa_id or not args.checkpoint_file:
        settings = get_agent_settings()
    empresa_id = args.empresa_id or (settings.empresa_id if settings else None)
    if not empresa_id:
        raise SystemExit("Missing --empresa-id or AGENT_EMPRESA_ID.")
    if not args.confirm:
        raise SystemExit("Refusing to change checkpoint without --confirm.")

    checkpoint_file = args.checkpoint_file or (settings.checkpoint_file if settings else "agent_local/data/checkpoints.json")
    checkpoint_key = f"{empresa_id}:{args.entity}"
    reset_value = CheckpointStore(checkpoint_file).reset(
        checkpoint_key,
        parse_checkpoint_datetime(args.since),
    )
    print(f"{checkpoint_key}={reset_value.astimezone(UTC).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
