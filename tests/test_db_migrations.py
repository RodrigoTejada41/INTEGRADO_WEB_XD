from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from backend.db.migration_runner import downgrade, get_current_version, upgrade


def _make_engine(db_file: Path):
    db_file.parent.mkdir(parents=True, exist_ok=True)
    if db_file.exists():
        db_file.unlink()
    return create_engine(f"sqlite+pysqlite:///{db_file.as_posix()}", future=True)


def test_upgrade_is_idempotent_and_tracks_current_version() -> None:
    db_file = Path("output/test_db_migrations_apply.db")
    engine = _make_engine(db_file)

    assert get_current_version(engine) == 0

    first_run = upgrade(engine)
    assert [migration.version for migration in first_run] == [1, 2, 3]
    assert get_current_version(engine) == 3

    second_run = upgrade(engine)
    assert second_run == []
    assert get_current_version(engine) == 3

    with engine.connect() as connection:
        row_count = connection.execute(
            text("SELECT COUNT(*) FROM sync_schema_migrations")
        ).scalar_one()
        tenant_columns = connection.execute(text("PRAGMA table_info(tenants)")).fetchall()
        client_columns = connection.execute(text("PRAGMA table_info(local_clients)")).fetchall()
    assert row_count == 3
    assert "api_key_expires_at" in {str(row[1]) for row in tenant_columns}
    assert "last_status_json" in {str(row[1]) for row in client_columns}
    engine.dispose()


def test_downgrade_by_steps_reverts_schema_version() -> None:
    db_file = Path("output/test_db_migrations_rollback.db")
    engine = _make_engine(db_file)

    upgrade(engine)
    rolled_back = downgrade(engine, steps=1)
    assert [migration.version for migration in rolled_back] == [3]
    assert get_current_version(engine) == 2

    with engine.connect() as connection:
        client_tables = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type = 'table' AND name = 'local_clients'
                """
            )
        ).scalar_one()
        migrations_count = connection.execute(
            text("SELECT COUNT(*) FROM sync_schema_migrations")
        ).scalar_one()

    assert client_tables == 0
    assert migrations_count == 2

    rolled_back_to_zero = downgrade(engine, steps=1)
    assert [migration.version for migration in rolled_back_to_zero] == [2]
    assert get_current_version(engine) == 1

    with engine.connect() as connection:
        tenant_columns = connection.execute(text("PRAGMA table_info(tenants)")).fetchall()
        audit_columns = connection.execute(text("PRAGMA table_info(tenant_audit_events)")).fetchall()
        migrations_count_after_v2 = connection.execute(
            text("SELECT COUNT(*) FROM sync_schema_migrations")
        ).scalar_one()

    assert "api_key_expires_at" not in {str(row[1]) for row in tenant_columns}
    assert "correlation_id" not in {str(row[1]) for row in audit_columns}
    assert migrations_count_after_v2 == 1

    rolled_back_initial = downgrade(engine, steps=1)
    assert [migration.version for migration in rolled_back_initial] == [1]
    assert get_current_version(engine) == 0

    with engine.connect() as connection:
        vendas_exists = connection.execute(
            text(
                """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type = 'table' AND name = 'vendas'
                """
            )
        ).scalar_one()
        final_migrations_count = connection.execute(
            text("SELECT COUNT(*) FROM sync_schema_migrations")
        ).scalar_one()

    assert vendas_exists == 0
    assert final_migrations_count == 0
    engine.dispose()
