from pathlib import Path

from sqlalchemy import text

from backend.config.database import engine


def run_migrations() -> None:
    migration_dir = Path(__file__).resolve().parent.parent / "migrations"
    files = sorted(migration_dir.glob("*.sql"))
    if not files:
        print("No migrations found.")
        return
    with engine.begin() as connection:
        for file in files:
            sql = file.read_text(encoding="utf-8")
            connection.execute(text(sql))
            print(f"Applied migration: {file.name}")


if __name__ == "__main__":
    run_migrations()
