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
from backend.db.migration_runner import downgrade, get_current_version


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rollback versioned schema migrations.")
    parser.add_argument(
        "--to",
        type=int,
        default=None,
        help="Target schema version to rollback to (inclusive).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="How many versions to rollback when --to is not provided.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    Path("output").mkdir(parents=True, exist_ok=True)
    rolled_back = downgrade(engine, target_version=args.to, steps=args.steps)
    current = get_current_version(engine)

    if not rolled_back:
        print(f"ROLLBACK OK - no applied migrations (current_version={current})")
        return 0

    rolled_back_versions = ", ".join(str(item.version) for item in rolled_back)
    print(
        "ROLLBACK OK - "
        f"rolled_back_versions=[{rolled_back_versions}] current_version={current}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
