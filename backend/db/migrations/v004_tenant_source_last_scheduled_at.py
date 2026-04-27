from __future__ import annotations

from sqlalchemy import Engine, text

VERSION = 4
NAME = "tenant_source_schedule_timestamps"


def _get_columns(engine: Engine, table_name: str) -> set[str]:
    if engine.dialect.name == "sqlite":
        with engine.connect() as connection:
            rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {str(row[1]) for row in rows}

    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table_name
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"table_name": table_name}).fetchall()
    return {str(row[0]) for row in rows}


def _add_column_if_missing(engine: Engine, table_name: str, column_name: str, column_sql: str) -> None:
    if column_name in _get_columns(engine, table_name):
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}"))


def upgrade(engine: Engine) -> None:
    _add_column_if_missing(
        engine,
        "tenant_source_configs",
        "last_scheduled_at",
        "last_scheduled_at TIMESTAMP NULL",
    )
    _add_column_if_missing(
        engine,
        "tenant_source_configs",
        "next_run_at",
        "next_run_at TIMESTAMP NULL",
    )


def downgrade(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text("ALTER TABLE tenant_source_configs RENAME TO tenant_source_configs_old"))
            connection.execute(
                text(
                    """
                    CREATE TABLE tenant_source_configs (
                        id VARCHAR(36) PRIMARY KEY,
                        empresa_id VARCHAR(32) NOT NULL,
                        nome VARCHAR(120) NOT NULL,
                        connector_type VARCHAR(32) NOT NULL,
                        sync_interval_minutes INTEGER NOT NULL DEFAULT 15,
                        settings_json TEXT NOT NULL DEFAULT '{}',
                        ativo BOOLEAN NOT NULL DEFAULT TRUE,
                        last_run_at TIMESTAMP NULL,
                        next_run_at TIMESTAMP NULL,
                        last_status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        last_error TEXT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL,
                        UNIQUE (empresa_id, nome)
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO tenant_source_configs (
                        id,
                        empresa_id,
                        nome,
                        connector_type,
                        sync_interval_minutes,
                        settings_json,
                        ativo,
                        last_run_at,
                        next_run_at,
                        last_status,
                        last_error,
                        created_at,
                        updated_at
                    )
                    SELECT
                        id,
                        empresa_id,
                        nome,
                        connector_type,
                        sync_interval_minutes,
                        settings_json,
                        ativo,
                        last_run_at,
                        next_run_at,
                        last_status,
                        last_error,
                        created_at,
                        updated_at
                    FROM tenant_source_configs_old
                    """
                )
            )
            connection.execute(text("DROP TABLE tenant_source_configs_old"))
            connection.execute(text("CREATE INDEX ix_tenant_source_configs_empresa_id ON tenant_source_configs (empresa_id)"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tenant_source_configs DROP COLUMN IF EXISTS next_run_at"))
        connection.execute(text("ALTER TABLE tenant_source_configs DROP COLUMN IF EXISTS last_scheduled_at"))
