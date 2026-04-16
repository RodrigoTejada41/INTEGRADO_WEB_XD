from __future__ import annotations

import hashlib
import json
import logging

from sqlalchemy.orm import Session

from app.core.security import hash_api_key, make_key_prefix
from app.repositories.integration_repository import IntegrationRepository
from app.repositories.sync_repository import SyncRepository

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, db: Session):
        self.db = db
        self.sync_repo = SyncRepository(db)
        self.int_repo = IntegrationRepository(db)

    def ensure_default_api_key(self, raw_key: str) -> None:
        key_hash = hash_api_key(raw_key)
        found = self.int_repo.by_hash(key_hash)
        if found:
            return
        self.int_repo.create(key_hash=key_hash, key_prefix=make_key_prefix(raw_key), description='Default bootstrap key')

    def authenticate_integration(self, raw_key: str):
        key_hash = hash_api_key(raw_key)
        entity = self.int_repo.by_hash(key_hash)
        if not entity:
            return None
        self.int_repo.touch_used(entity)
        return entity

    def ingest_payload(self, payload: dict, source_ip: str) -> dict:
        serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        payload_hash = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        records_in = payload.get('records', [])

        batch = self.sync_repo.create_batch(
            external_batch_id=payload.get('external_batch_id'),
            company_code=payload['company_code'],
            branch_code=payload['branch_code'],
            terminal_code=payload['terminal_code'],
            source_ip=source_ip,
            status='success',
            records_received=len(records_in),
            payload_hash=payload_hash,
            error_message=None,
        )

        records = []
        for r in records_in:
            records.append(
                {
                    'record_key': r['record_key'],
                    'record_type': r['record_type'],
                    'event_time': r.get('event_time'),
                    'payload_json': json.dumps(r['payload'], ensure_ascii=True, sort_keys=True),
                }
            )

        if records:
            self.sync_repo.add_records(batch.id, records)

        logger.info(
            'sync_ingested batch_id=%s records=%s source_ip=%s company=%s branch=%s terminal=%s',
            batch.id,
            len(records),
            source_ip,
            payload['company_code'],
            payload['branch_code'],
            payload['terminal_code'],
        )

        return {'batch_id': batch.id, 'records_received': len(records)}
