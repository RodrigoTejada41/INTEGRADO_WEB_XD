from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.sync_batch import SyncBatch
from app.models.sync_record import SyncRecord


class SyncRepository:
    def __init__(self, db: Session):
        self.db = db

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

    def list_records(self, *, page: int, page_size: int, search: str | None, record_type: str | None, sort: str = 'created_at'):
        stmt = select(SyncRecord)
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

    def list_batches(self, *, page: int, page_size: int, status: str | None):
        stmt = select(SyncBatch)
        if status:
            stmt = stmt.where(SyncBatch.status == status)
        stmt = stmt.order_by(desc(SyncBatch.received_at))
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
        return rows, total

    def dashboard_counts(self) -> dict:
        total_records = self.db.execute(select(func.count(SyncRecord.id))).scalar_one() or 0
        total_batches = self.db.execute(select(func.count(SyncBatch.id))).scalar_one() or 0
        failed_batches = self.db.execute(select(func.count(SyncBatch.id)).where(SyncBatch.status == 'failed')).scalar_one() or 0
        last_received = self.db.execute(select(func.max(SyncBatch.received_at))).scalar_one()
        return {
            'total_records': total_records,
            'total_batches': total_batches,
            'failed_batches': failed_batches,
            'last_received': last_received,
        }

    def chart_by_day(self, days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.date(SyncBatch.received_at).label('d'), func.sum(SyncBatch.records_received).label('q'))
            .where(SyncBatch.received_at >= cutoff)
            .group_by(func.date(SyncBatch.received_at))
            .order_by(func.date(SyncBatch.received_at))
        )
        rows = self.db.execute(stmt).all()
        return [{'label': str(r.d), 'value': int(r.q or 0)} for r in rows]

    def latest_batches(self, limit: int = 10) -> list[SyncBatch]:
        stmt = select(SyncBatch).order_by(desc(SyncBatch.received_at)).limit(limit)
        return self.db.execute(stmt).scalars().all()
