from __future__ import annotations

from sqlalchemy import Engine, text

VERSION = 5
NAME = "sales_report_dimensions"


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
    for table_name in ("vendas", "vendas_historico"):
        _add_column_if_missing(engine, table_name, "tipo_venda", "tipo_venda VARCHAR(80) NULL")
        _add_column_if_missing(engine, table_name, "forma_pagamento", "forma_pagamento VARCHAR(120) NULL")
        _add_column_if_missing(engine, table_name, "familia_produto", "familia_produto VARCHAR(160) NULL")

    if engine.dialect.name != "sqlite":
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_tipo ON vendas (empresa_id, tipo_venda)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_pagamento ON vendas (empresa_id, forma_pagamento)")
            )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_familia ON vendas (empresa_id, familia_produto)")
            )


def downgrade(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        return
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_tipo"))
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_pagamento"))
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_familia"))
        connection.execute(text("ALTER TABLE vendas DROP COLUMN IF EXISTS tipo_venda"))
        connection.execute(text("ALTER TABLE vendas DROP COLUMN IF EXISTS forma_pagamento"))
        connection.execute(text("ALTER TABLE vendas DROP COLUMN IF EXISTS familia_produto"))
        connection.execute(text("ALTER TABLE vendas_historico DROP COLUMN IF EXISTS tipo_venda"))
        connection.execute(text("ALTER TABLE vendas_historico DROP COLUMN IF EXISTS forma_pagamento"))
        connection.execute(text("ALTER TABLE vendas_historico DROP COLUMN IF EXISTS familia_produto"))
