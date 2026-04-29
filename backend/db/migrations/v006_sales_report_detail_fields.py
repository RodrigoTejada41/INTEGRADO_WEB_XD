from __future__ import annotations

from sqlalchemy import Engine, text

VERSION = 6
NAME = "sales_report_detail_fields"


DETAIL_COLUMNS = {
    "bandeira_cartao": "VARCHAR(80) NULL",
    "categoria_produto": "VARCHAR(160) NULL",
    "codigo_produto_local": "VARCHAR(120) NULL",
    "unidade": "VARCHAR(30) NULL",
    "operador": "VARCHAR(120) NULL",
    "cliente": "VARCHAR(160) NULL",
    "status_venda": "VARCHAR(80) NULL",
    "cancelada": "BOOLEAN NOT NULL DEFAULT FALSE",
    "quantidade": "NUMERIC(14,3) NOT NULL DEFAULT 1",
    "valor_unitario": "NUMERIC(14,4) NULL",
    "valor_bruto": "NUMERIC(14,2) NULL",
    "desconto": "NUMERIC(14,2) NOT NULL DEFAULT 0",
    "acrescimo": "NUMERIC(14,2) NOT NULL DEFAULT 0",
    "valor_liquido": "NUMERIC(14,2) NULL",
}


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
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def upgrade(engine: Engine) -> None:
    with engine.begin() as connection:
        id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if engine.dialect.name == "sqlite" else "BIGSERIAL PRIMARY KEY"
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS produto_de_para (
                    id {id_type},
                    empresa_id VARCHAR(32) NOT NULL REFERENCES tenants (empresa_id) ON DELETE CASCADE,
                    cnpj VARCHAR(32) NOT NULL,
                    codigo_produto_local VARCHAR(120) NOT NULL,
                    codigo_produto_web VARCHAR(120) NULL,
                    descricao_produto_local VARCHAR(255) NULL,
                    descricao_produto_web VARCHAR(255) NULL,
                    familia_local VARCHAR(160) NULL,
                    familia_web VARCHAR(160) NULL,
                    categoria_local VARCHAR(160) NULL,
                    categoria_web VARCHAR(160) NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_produto_de_para_empresa_codigo_local UNIQUE (empresa_id, codigo_produto_local)
                )
                """
            )
        )

    for table_name in ("vendas", "vendas_historico"):
        for column_name, column_sql in DETAIL_COLUMNS.items():
            _add_column_if_missing(engine, table_name, column_name, column_sql)

    if engine.dialect.name != "sqlite":
        with engine.begin() as connection:
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_codigo_produto ON vendas (empresa_id, codigo_produto_local)")
            )
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_categoria ON vendas (empresa_id, categoria_produto)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_operador ON vendas (empresa_id, operador)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vendas_empresa_status ON vendas (empresa_id, status_venda, cancelada)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_produto_de_para_empresa_codigo_local ON produto_de_para (empresa_id, codigo_produto_local)")
            )


def downgrade(engine: Engine) -> None:
    if engine.dialect.name == "sqlite":
        return
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_codigo_produto"))
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_categoria"))
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_operador"))
        connection.execute(text("DROP INDEX IF EXISTS ix_vendas_empresa_status"))
        connection.execute(text("DROP INDEX IF EXISTS ix_produto_de_para_empresa_codigo_local"))
        connection.execute(text("DROP TABLE IF EXISTS produto_de_para"))
        for table_name in ("vendas", "vendas_historico"):
            for column_name in DETAIL_COLUMNS:
                connection.execute(text(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name}"))
