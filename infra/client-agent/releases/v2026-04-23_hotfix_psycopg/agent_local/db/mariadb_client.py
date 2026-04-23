from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


class MariaDBClient:
    def __init__(self, mariadb_url: str, source_query: str | None = None):
        self.engine = create_engine(mariadb_url, pool_pre_ping=True, future=True)
        self.session_factory = sessionmaker(bind=self.engine, class_=Session, autoflush=False)
        self.source_query = source_query

    def fetch_changed_vendas(
        self,
        empresa_id: str,
        since: datetime,
        limit: int,
    ) -> list[dict]:
        if self.source_query:
            stmt = text(self.source_query)
            params = {"empresa_id": empresa_id, "since": since, "limit": limit}
        else:
            stmt = text(
                """
                SELECT
                    uuid,
                    empresa_id,
                    produto,
                    valor,
                    data,
                    data_atualizacao
                FROM vendas
                WHERE empresa_id = :empresa_id
                  AND data_atualizacao > :since
                ORDER BY data_atualizacao ASC
                LIMIT :limit
                """
            )
            params = {"empresa_id": empresa_id, "since": since, "limit": limit}

        with self.session_factory() as session:
            rows = session.execute(stmt, params).mappings()
            items = []
            for row in rows:
                data_atualizacao = row["data_atualizacao"]
                if data_atualizacao.tzinfo is None:
                    data_atualizacao = data_atualizacao.replace(tzinfo=UTC)
                items.append(
                    {
                        "uuid": str(row["uuid"]),
                        "empresa_id": str(row["empresa_id"]),
                        "produto": row["produto"],
                        "valor": str(row["valor"]),
                        "data": row["data"].isoformat(),
                        "data_atualizacao": data_atualizacao.isoformat(),
                    }
                )
            return items

    def ping(self) -> bool:
        stmt = text("SELECT 1")
        with self.session_factory() as session:
            session.execute(stmt)
        return True
