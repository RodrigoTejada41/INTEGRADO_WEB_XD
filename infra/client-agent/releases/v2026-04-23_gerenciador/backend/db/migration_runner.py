from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, text

from backend.db.migrations import Migration, list_migrations

MIGRATIONS_TABLE = "sync_schema_migrations"


def _ensure_migrations_table(engine: Engine) -> None:
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
        version INTEGER PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        applied_at TIMESTAMP NOT NULL
    )
    """
    with engine.begin() as connection:
        connection.execute(text(create_sql))


def get_applied_versions(engine: Engine) -> list[int]:
    _ensure_migrations_table(engine)
    query = text(f"SELECT version FROM {MIGRATIONS_TABLE} ORDER BY version")
    with engine.connect() as connection:
        rows = connection.execute(query).fetchall()
    return [int(row[0]) for row in rows]


def get_current_version(engine: Engine) -> int:
    applied = get_applied_versions(engine)
    return applied[-1] if applied else 0


def upgrade(engine: Engine, target_version: int | None = None) -> list[Migration]:
    _ensure_migrations_table(engine)
    migrations = list_migrations()
    applied_versions = set(get_applied_versions(engine))

    selected: list[Migration] = []
    for migration in migrations:
        if migration.version in applied_versions:
            continue
        if target_version is not None and migration.version > target_version:
            continue
        selected.append(migration)

    for migration in selected:
        with engine.begin() as connection:
            migration.upgrade(engine)
            connection.execute(
                text(
                    f"""
                    INSERT INTO {MIGRATIONS_TABLE} (version, name, applied_at)
                    VALUES (:version, :name, :applied_at)
                    """
                ),
                {
                    "version": migration.version,
                    "name": migration.name,
                    "applied_at": datetime.now(UTC).replace(tzinfo=None),
                },
            )

    return selected


def downgrade(
    engine: Engine,
    target_version: int | None = None,
    steps: int = 1,
) -> list[Migration]:
    _ensure_migrations_table(engine)
    migrations = {migration.version: migration for migration in list_migrations()}
    applied_versions = get_applied_versions(engine)

    if not applied_versions:
        return []

    if target_version is None:
        if steps <= 0:
            raise ValueError("steps must be greater than zero.")
        rollback_versions = applied_versions[-steps:]
    else:
        rollback_versions = [version for version in applied_versions if version > target_version]

    rollback_versions = sorted(rollback_versions, reverse=True)
    rolled_back: list[Migration] = []

    for version in rollback_versions:
        migration = migrations.get(version)
        if migration is None:
            raise RuntimeError(f"Missing migration file for version {version}.")

        with engine.begin() as connection:
            migration.downgrade(engine)
            connection.execute(
                text(f"DELETE FROM {MIGRATIONS_TABLE} WHERE version = :version"),
                {"version": version},
            )
        rolled_back.append(migration)

    return rolled_back

