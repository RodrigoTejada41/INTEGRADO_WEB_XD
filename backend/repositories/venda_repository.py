from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from backend.models.venda import Venda, VendaHistorico


class VendaRepository:
    def __init__(self, session: Session):
        self.session = session

    def bulk_upsert(self, empresa_id: str, records: list[dict]) -> tuple[int, int]:
        if not records:
            return 0, 0

        canonical_records = self._deduplicate_by_uuid(records)
        uuids = [record["uuid"] for record in canonical_records]

        existing_stmt = select(Venda.uuid).where(Venda.empresa_id == empresa_id, Venda.uuid.in_(uuids))
        existing_uuids = set(self.session.scalars(existing_stmt).all())
        inserted_count = len(set(uuids) - existing_uuids)
        updated_count = len(set(uuids) & existing_uuids)

        values = []
        for item in canonical_records:
            values.append(
                {
                    "uuid": item["uuid"],
                    "empresa_id": empresa_id,
                    "branch_code": item.get("branch_code"),
                    "terminal_code": item.get("terminal_code"),
                    "produto": item["produto"],
                    "valor": item["valor"],
                    "data": item["data"],
                    "data_atualizacao": item["data_atualizacao"],
                    "updated_at": datetime.now(UTC),
                }
            )

        dialect_name = self.session.bind.dialect.name if self.session.bind else "default"
        if dialect_name == "postgresql":
            stmt = pg_insert(Venda).values(values)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["empresa_id", "uuid"],
                set_={
                    "produto": stmt.excluded.produto,
                    "branch_code": stmt.excluded.branch_code,
                    "terminal_code": stmt.excluded.terminal_code,
                    "valor": stmt.excluded.valor,
                    "data": stmt.excluded.data,
                    "data_atualizacao": stmt.excluded.data_atualizacao,
                    "updated_at": datetime.now(UTC),
                },
            )
            self.session.execute(upsert_stmt)
        elif dialect_name == "sqlite":
            stmt = sqlite_insert(Venda).values(values)
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["empresa_id", "uuid"],
                set_={
                    "produto": stmt.excluded.produto,
                    "branch_code": stmt.excluded.branch_code,
                    "terminal_code": stmt.excluded.terminal_code,
                    "valor": stmt.excluded.valor,
                    "data": stmt.excluded.data,
                    "data_atualizacao": stmt.excluded.data_atualizacao,
                    "updated_at": datetime.now(UTC),
                },
            )
            self.session.execute(upsert_stmt)
        else:
            for value in values:
                self.session.execute(
                    delete(Venda).where(Venda.empresa_id == empresa_id, Venda.uuid == value["uuid"])
                )
                self.session.execute(insert(Venda).values(**value))

        return inserted_count, updated_count

    def retain_recent_data(self, cutoff_date, mode: str) -> int:
        to_remove_subq = select(Venda).where(Venda.data < cutoff_date).subquery()
        count_stmt = select(func.count()).select_from(to_remove_subq)
        rows_to_process = self.session.scalar(count_stmt) or 0
        if rows_to_process == 0:
            return 0

        if mode == "archive":
            archive_stmt = insert(VendaHistorico).from_select(
                [
                    "uuid",
                    "empresa_id",
                    "produto",
                    "branch_code",
                    "terminal_code",
                    "valor",
                    "data",
                    "data_atualizacao",
                    "arquivado_em",
                ],
                select(
                    Venda.uuid,
                    Venda.empresa_id,
                    Venda.produto,
                    Venda.branch_code,
                    Venda.terminal_code,
                    Venda.valor,
                    Venda.data,
                    Venda.data_atualizacao,
                    func.now(),
                ).where(Venda.data < cutoff_date),
            )
            self.session.execute(archive_stmt)

        purge_stmt = delete(Venda).where(Venda.data < cutoff_date)
        self.session.execute(purge_stmt)
        return rows_to_process

    @staticmethod
    def _deduplicate_by_uuid(records: list[dict]) -> list[dict]:
        grouped: dict[str, dict] = {}
        for record in records:
            uuid = record["uuid"]
            previous = grouped.get(uuid)
            if not previous or record["data_atualizacao"] >= previous["data_atualizacao"]:
                grouped[uuid] = record
        return list(grouped.values())

