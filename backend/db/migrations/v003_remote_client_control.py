from __future__ import annotations

from sqlalchemy import Engine, text

VERSION = 3
NAME = "remote_client_control"


def _table_exists(engine: Engine, table_name: str) -> bool:
    if engine.dialect.name == "sqlite":
        query = text(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type = 'table' AND name = :table_name
            """
        )
    else:
        query = text(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = :table_name
            """
        )
    with engine.connect() as connection:
        return int(connection.execute(query, {"table_name": table_name}).scalar_one()) > 0


def upgrade(engine: Engine) -> None:
    with engine.begin() as connection:
        if not _table_exists(engine, "local_clients"):
            connection.execute(
                text(
                    """
                    CREATE TABLE local_clients (
                        id VARCHAR(36) PRIMARY KEY,
                        empresa_id VARCHAR(32) NOT NULL,
                        hostname VARCHAR(255) NOT NULL,
                        ip_address VARCHAR(64) NULL,
                        endpoint_url VARCHAR(255) NULL,
                        token_hash VARCHAR(128) NOT NULL,
                        token_last_rotated_at TIMESTAMP NULL,
                        token_expires_at TIMESTAMP NULL,
                        status VARCHAR(24) NOT NULL DEFAULT 'online',
                        last_seen_at TIMESTAMP NULL,
                        last_sync_at TIMESTAMP NULL,
                        last_command_poll_at TIMESTAMP NULL,
                        last_config_json TEXT NOT NULL DEFAULT '{}',
                        last_status_json TEXT NOT NULL DEFAULT '{}',
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX ix_local_clients_empresa_id ON local_clients (empresa_id)"))
            connection.execute(text("CREATE INDEX ix_local_clients_last_seen_at ON local_clients (last_seen_at)"))
            connection.execute(text("CREATE INDEX ix_local_clients_hostname ON local_clients (hostname)"))

        if not _table_exists(engine, "local_client_commands"):
            connection.execute(
                text(
                    """
                    CREATE TABLE local_client_commands (
                        id VARCHAR(36) PRIMARY KEY,
                        client_id VARCHAR(36) NOT NULL,
                        empresa_id VARCHAR(32) NOT NULL,
                        command_type VARCHAR(80) NOT NULL,
                        payload_json TEXT NOT NULL DEFAULT '{}',
                        status VARCHAR(24) NOT NULL DEFAULT 'pending',
                        requested_by VARCHAR(120) NOT NULL DEFAULT 'system',
                        origin VARCHAR(80) NOT NULL DEFAULT 'web',
                        result_json TEXT NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL,
                        delivered_at TIMESTAMP NULL,
                        executed_at TIMESTAMP NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX ix_local_client_commands_client_status ON local_client_commands (client_id, status)"
                )
            )
            connection.execute(text("CREATE INDEX ix_local_client_commands_empresa_id ON local_client_commands (empresa_id)"))
            connection.execute(text("CREATE INDEX ix_local_client_commands_created_at ON local_client_commands (created_at)"))

        if not _table_exists(engine, "local_client_logs"):
            connection.execute(
                text(
                    """
                    CREATE TABLE local_client_logs (
                        id VARCHAR(36) PRIMARY KEY,
                        client_id VARCHAR(36) NOT NULL,
                        empresa_id VARCHAR(32) NOT NULL,
                        direction VARCHAR(24) NOT NULL,
                        event_type VARCHAR(80) NOT NULL,
                        origin VARCHAR(120) NOT NULL,
                        status VARCHAR(24) NOT NULL DEFAULT 'success',
                        message VARCHAR(255) NULL,
                        detail_json TEXT NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX ix_local_client_logs_client_created ON local_client_logs (client_id, created_at)"
                )
            )
            connection.execute(text("CREATE INDEX ix_local_client_logs_empresa_id ON local_client_logs (empresa_id)"))


def downgrade(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS local_client_logs"))
        connection.execute(text("DROP TABLE IF EXISTS local_client_commands"))
        connection.execute(text("DROP TABLE IF EXISTS local_clients"))
