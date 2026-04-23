from __future__ import annotations

from sqlalchemy import Engine, text

VERSION = 2
NAME = "tenant_secret_governance"


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
        "tenants",
        "api_key_last_rotated_at",
        "api_key_last_rotated_at TIMESTAMP NULL",
    )
    _add_column_if_missing(
        engine,
        "tenants",
        "api_key_expires_at",
        "api_key_expires_at TIMESTAMP NULL",
    )
    _add_column_if_missing(
        engine,
        "tenant_audit_events",
        "correlation_id",
        "correlation_id VARCHAR(128) NULL",
    )
    _add_column_if_missing(
        engine,
        "tenant_audit_events",
        "request_path",
        "request_path VARCHAR(255) NULL",
    )
    _add_column_if_missing(
        engine,
        "tenant_audit_events",
        "actor_ip",
        "actor_ip VARCHAR(64) NULL",
    )
    _add_column_if_missing(
        engine,
        "tenant_audit_events",
        "user_agent",
        "user_agent VARCHAR(255) NULL",
    )

    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.execute(
                text(
                    """
                    UPDATE tenants
                    SET api_key_last_rotated_at = COALESCE(api_key_last_rotated_at, updated_at, created_at)
                    WHERE api_key_last_rotated_at IS NULL
                    """
                )
            )
            connection.execute(
                text(
                    """
                    UPDATE tenants
                    SET api_key_expires_at = datetime(
                        COALESCE(api_key_last_rotated_at, updated_at, created_at),
                        '+90 days'
                    )
                    WHERE api_key_expires_at IS NULL
                    """
                )
            )
            return

        connection.execute(
            text(
                """
                UPDATE tenants
                SET api_key_last_rotated_at = COALESCE(api_key_last_rotated_at, updated_at, created_at)
                WHERE api_key_last_rotated_at IS NULL
                """
            )
        )
        connection.execute(
            text(
                """
                UPDATE tenants
                SET api_key_expires_at = COALESCE(
                    api_key_expires_at,
                    api_key_last_rotated_at + INTERVAL '90 days',
                    updated_at + INTERVAL '90 days',
                    created_at + INTERVAL '90 days'
                )
                WHERE api_key_expires_at IS NULL
                """
            )
        )


def downgrade(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text("ALTER TABLE tenant_audit_events RENAME TO tenant_audit_events_old"))
            connection.execute(
                text(
                    """
                    CREATE TABLE tenant_audit_events (
                        id VARCHAR(36) PRIMARY KEY,
                        empresa_id VARCHAR(32) NOT NULL,
                        actor VARCHAR(120) NOT NULL,
                        action VARCHAR(80) NOT NULL,
                        resource_type VARCHAR(80) NOT NULL,
                        resource_id VARCHAR(120) NULL,
                        status VARCHAR(24) NOT NULL DEFAULT 'success',
                        detail_json TEXT NOT NULL DEFAULT '{}',
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO tenant_audit_events (
                        id,
                        empresa_id,
                        actor,
                        action,
                        resource_type,
                        resource_id,
                        status,
                        detail_json,
                        created_at
                    )
                    SELECT
                        id,
                        empresa_id,
                        actor,
                        action,
                        resource_type,
                        resource_id,
                        status,
                        detail_json,
                        created_at
                    FROM tenant_audit_events_old
                    """
                )
            )
            connection.execute(text("DROP TABLE tenant_audit_events_old"))
            connection.execute(text("CREATE INDEX ix_tenant_audit_events_empresa_id ON tenant_audit_events (empresa_id)"))
            connection.execute(text("CREATE INDEX ix_tenant_audit_events_created_at ON tenant_audit_events (created_at)"))
            connection.execute(text("CREATE INDEX ix_tenant_audit_events_action ON tenant_audit_events (action)"))

            connection.execute(text("ALTER TABLE tenants RENAME TO tenants_old"))
            connection.execute(
                text(
                    """
                    CREATE TABLE tenants (
                        empresa_id VARCHAR(32) PRIMARY KEY,
                        nome VARCHAR(120) NOT NULL,
                        api_key_hash VARCHAR(128) NOT NULL,
                        ativo BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO tenants (
                        empresa_id,
                        nome,
                        api_key_hash,
                        ativo,
                        created_at,
                        updated_at
                    )
                    SELECT
                        empresa_id,
                        nome,
                        api_key_hash,
                        ativo,
                        created_at,
                        updated_at
                    FROM tenants_old
                    """
                )
            )
            connection.execute(text("DROP TABLE tenants_old"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tenant_audit_events DROP COLUMN IF EXISTS correlation_id"))
        connection.execute(text("ALTER TABLE tenant_audit_events DROP COLUMN IF EXISTS request_path"))
        connection.execute(text("ALTER TABLE tenant_audit_events DROP COLUMN IF EXISTS actor_ip"))
        connection.execute(text("ALTER TABLE tenant_audit_events DROP COLUMN IF EXISTS user_agent"))
        connection.execute(text("ALTER TABLE tenants DROP COLUMN IF EXISTS api_key_last_rotated_at"))
        connection.execute(text("ALTER TABLE tenants DROP COLUMN IF EXISTS api_key_expires_at"))
