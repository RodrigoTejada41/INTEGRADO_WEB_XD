from __future__ import annotations

import argparse
import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./output/ci.db")
os.environ.setdefault("ADMIN_TOKEN", "admin-token-test")

from backend.config.database import engine
from backend.db.migration_runner import get_current_version, upgrade


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply versioned schema migrations.")
    parser.add_argument(
        "--to",
        type=int,
        default=None,
        help="Target schema version to apply up to (inclusive).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    Path("output").mkdir(parents=True, exist_ok=True)
    applied = upgrade(engine, target_version=args.to)
    current = get_current_version(engine)

    if not applied:
        print(f"MIGRATION OK - no pending migrations (current_version={current})")
        return 0

    applied_versions = ", ".join(str(item.version) for item in applied)
    print(
        "MIGRATION OK - "
        f"applied_versions=[{applied_versions}] current_version={current}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
