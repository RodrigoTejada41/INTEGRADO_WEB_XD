from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.sync_batch import SyncBatch
from app.models.sync_record import SyncRecord


class SyncRepository:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _apply_scope_filters(
        stmt,
        *,
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ):
        if company_code:
            stmt = stmt.where(SyncBatch.company_code == company_code)
        if branch_code:
            stmt = stmt.where(SyncBatch.branch_code == branch_code)
        if terminal_code:
            stmt = stmt.where(SyncBatch.terminal_code == terminal_code)
        return stmt

    def create_batch(
        self,
        *,
        external_batch_id: str | None,
        company_code: str,
        branch_code: str,
        terminal_code: str,
        source_ip: str,
        status: str,
        records_received: int,
        payload_hash: str,
        error_message: str | None,
    ) -> SyncBatch:
        batch = SyncBatch(
            external_batch_id=external_batch_id,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
            source_ip=source_ip,
            status=status,
            records_received=records_received,
            payload_hash=payload_hash,
            error_message=error_message,
        )
        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)
        return batch

    def add_records(self, batch_id: int, records: list[dict]) -> None:
        entities = [
            SyncRecord(
                batch_id=batch_id,
                record_key=r['record_key'],
                record_type=r['record_type'],
                event_time=r.get('event_time'),
                payload_json=r['payload_json'],
            )
            for r in records
        ]
        self.db.add_all(entities)
        self.db.commit()

    def list_records(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        record_type: str | None,
        sort: str = 'created_at',
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ):
        stmt = select(SyncRecord)
        stmt = stmt.join(SyncBatch, SyncRecord.batch_id == SyncBatch.id)
        stmt = self._apply_scope_filters(
            stmt,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        if search:
            like = f'%{search}%'
            stmt = stmt.where((SyncRecord.record_key.like(like)) | (SyncRecord.payload_json.like(like)))
        if record_type:
            stmt = stmt.where(SyncRecord.record_type == record_type)

        order_column = SyncRecord.created_at if sort not in {'record_key', 'record_type', 'event_time'} else getattr(SyncRecord, sort)
        stmt = stmt.order_by(desc(order_column))

        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return rows, total

    def list_batches(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None,
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ):
        stmt = select(SyncBatch)
        stmt = self._apply_scope_filters(
            stmt,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        if status:
            stmt = stmt.where(SyncBatch.status == status)
        stmt = stmt.order_by(desc(SyncBatch.received_at))
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return rows, total

    def dashboard_counts(
        self,
        *,
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> dict:
        batch_stmt = select(SyncBatch.id)
        batch_stmt = self._apply_scope_filters(
            batch_stmt,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        batch_ids = batch_stmt.subquery()
        total_records = self.db.execute(
            select(func.count(SyncRecord.id)).where(SyncRecord.batch_id.in_(select(batch_ids.c.id)))
        ).scalar_one() or 0
        total_batches = self.db.execute(select(func.count()).select_from(batch_ids)).scalar_one() or 0
        failed_batches = self.db.execute(
            select(func.count()).select_from(SyncBatch).where(
                SyncBatch.status == 'failed',
                *[
                    cond
                    for cond in [
                        SyncBatch.company_code == company_code if company_code else None,
                        SyncBatch.branch_code == branch_code if branch_code else None,
                        SyncBatch.terminal_code == terminal_code if terminal_code else None,
                    ]
                    if cond is not None
                ],
            )
        ).scalar_one() or 0
        last_received_stmt = select(func.max(SyncBatch.received_at))
        last_received_stmt = self._apply_scope_filters(
            last_received_stmt,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        last_received = self.db.execute(last_received_stmt).scalar_one()
        return {
            'total_records': total_records,
            'total_batches': total_batches,
            'failed_batches': failed_batches,
            'last_received': last_received,
        }

    def chart_by_day(
        self,
        days: int = 30,
        *,
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> list[dict]:
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.date(SyncBatch.received_at).label('d'), func.sum(SyncBatch.records_received).label('q'))
            .where(SyncBatch.received_at >= cutoff)
            .group_by(func.date(SyncBatch.received_at))
            .order_by(func.date(SyncBatch.received_at))
        )
        stmt = self._apply_scope_filters(
            stmt,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        rows = self.db.execute(stmt).all()
        return [{'label': str(r.d), 'value': int(r.q or 0)} for r in rows]

    def latest_batches(
        self,
        limit: int = 10,
        *,
        company_code: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
    ) -> list[SyncBatch]:
        stmt = select(SyncBatch).order_by(desc(SyncBatch.received_at)).limit(limit)
        stmt = self._apply_scope_filters(
            stmt,
            company_code=company_code,
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
        return self.db.execute(stmt).scalars().all()
