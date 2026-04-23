from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, desc, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from backend.models.venda import Venda, VendaHistorico


class VendaRepository:
    def __init__(self, session: Session):
        self.session = session

    def bulk_upsert(self, empresa_id: str, records: list[dict], *, chunk_size: int = 250) -> tuple[int, int]:
        if not records:
            return 0, 0

        canonical_records = self._deduplicate_by_uuid(records)
        inserted_count = 0
        updated_count = 0

        for chunk in self._chunked(canonical_records, max(1, chunk_size)):
            uuids = [record["uuid"] for record in chunk]
            existing_stmt = select(Venda.uuid).where(Venda.empresa_id == empresa_id, Venda.uuid.in_(uuids))
            existing_uuids = set(self.session.scalars(existing_stmt).all())
            inserted_count += len(set(uuids) - existing_uuids)
            updated_count += len(set(uuids) & existing_uuids)

            values = []
            for item in chunk:
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
                        "branch_code": stmt.excluded.branch_code,
                        "terminal_code": stmt.excluded.terminal_code,
                        "produto": stmt.excluded.produto,
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
                        "branch_code": stmt.excluded.branch_code,
                        "terminal_code": stmt.excluded.terminal_code,
                        "produto": stmt.excluded.produto,
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
                    "branch_code",
                    "terminal_code",
                    "produto",
                    "valor",
                    "data",
                    "data_atualizacao",
                    "arquivado_em",
                ],
                select(
                    Venda.uuid,
                    Venda.empresa_id,
                    Venda.branch_code,
                    Venda.terminal_code,
                    Venda.produto,
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

    def report_overview(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> dict[str, object]:
        stmt = select(
            func.count(Venda.id).label("total_records"),
            func.coalesce(func.sum(Venda.valor), 0).label("total_sales_value"),
            func.count(func.distinct(Venda.produto)).label("distinct_products"),
            func.count(func.distinct(Venda.branch_code)).label("distinct_branches"),
            func.count(func.distinct(Venda.terminal_code)).label("distinct_terminals"),
            func.min(Venda.data).label("first_sale_date"),
            func.max(Venda.data).label("last_sale_date"),
        )
        stmt = self._apply_report_filters(
            stmt,
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        row = self.session.execute(stmt).one()
        return {
            "total_records": int(row.total_records or 0),
            "total_sales_value": Decimal(str(row.total_sales_value or 0)),
            "distinct_products": int(row.distinct_products or 0),
            "distinct_branches": int(row.distinct_branches or 0),
            "distinct_terminals": int(row.distinct_terminals or 0),
            "first_sale_date": row.first_sale_date,
            "last_sale_date": row.last_sale_date,
        }

    def report_daily_sales(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> list[dict[str, object]]:
        stmt = select(
            Venda.data.label("day"),
            func.count(Venda.id).label("total_records"),
            func.coalesce(func.sum(Venda.valor), 0).label("total_sales_value"),
        ).group_by(Venda.data).order_by(Venda.data.asc())
        stmt = self._apply_report_filters(
            stmt,
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "day": row.day,
                "total_records": int(row.total_records or 0),
                "total_sales_value": Decimal(str(row.total_sales_value or 0)),
            }
            for row in rows
        ]

    def report_top_products(
        self,
        *,
        empresa_id: str,
        limit: int,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> list[dict[str, object]]:
        stmt = (
            select(
                Venda.produto,
                func.count(Venda.id).label("total_records"),
                func.coalesce(func.sum(Venda.valor), 0).label("total_sales_value"),
            )
            .group_by(Venda.produto)
            .order_by(desc("total_sales_value"), desc("total_records"), Venda.produto.asc())
            .limit(limit)
        )
        stmt = self._apply_report_filters(
            stmt,
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "produto": row.produto,
                "total_records": int(row.total_records or 0),
                "total_sales_value": Decimal(str(row.total_sales_value or 0)),
            }
            for row in rows
        ]

    def report_recent_sales(
        self,
        *,
        empresa_id: str,
        limit: int,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> list[Venda]:
        stmt = select(Venda).order_by(Venda.data_atualizacao.desc(), Venda.id.desc()).limit(limit)
        stmt = self._apply_report_filters(
            stmt,
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        return list(self.session.scalars(stmt).all())

    def report_branch_codes(
        self,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        terminal_code: str | None = None,
    ) -> list[str]:
        stmt = (
            select(Venda.branch_code)
            .where(Venda.branch_code.is_not(None))
            .distinct()
            .order_by(Venda.branch_code.asc())
        )
        stmt = self._apply_report_filters(
            stmt,
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            terminal_code=terminal_code,
        )
        return [str(item) for item in self.session.scalars(stmt).all() if item]

    @staticmethod
    def _deduplicate_by_uuid(records: list[dict]) -> list[dict]:
        grouped: dict[str, dict] = {}
        for record in records:
            uuid = record["uuid"]
            previous = grouped.get(uuid)
            if not previous or record["data_atualizacao"] >= previous["data_atualizacao"]:
                grouped[uuid] = record
        return list(grouped.values())

    @staticmethod
    def _chunked(records: list[dict], size: int) -> list[list[dict]]:
        return [records[index : index + size] for index in range(0, len(records), size)]

    @staticmethod
    def _apply_report_filters(
        stmt,
        *,
        empresa_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ):
        stmt = stmt.where(Venda.empresa_id == empresa_id)
        if start_date is not None:
            stmt = stmt.where(Venda.data >= start_date)
        if end_date is not None:
            stmt = stmt.where(Venda.data <= end_date)
        if branch_code:
            stmt = stmt.where(Venda.branch_code == branch_code)
        if terminal_code:
            stmt = stmt.where(Venda.terminal_code == terminal_code)
        return stmt
