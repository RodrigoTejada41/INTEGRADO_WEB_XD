from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.sync import SyncPayloadIn
from app.services.sync_service import SyncService

router = APIRouter(prefix='/api', tags=['sync'])
logger = logging.getLogger(__name__)


@router.post('/sync-data')
def sync_data(
    payload: SyncPayloadIn,
    request: Request,
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    db: Session = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing X-API-Key')

    svc = SyncService(db)
    key = svc.authenticate_integration(x_api_key)
    if not key:
        logger.warning('sync_auth_failed source_ip=%s', request.client.host if request.client else 'unknown')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid integration key')

    source_ip = request.headers.get('X-Forwarded-For') or (request.client.host if request.client else 'unknown')

    try:
        result = svc.ingest_payload(payload.model_dump(mode='json'), source_ip=source_ip)
        return {
            'status': 'ok',
            'batch_id': result['batch_id'],
            'records_received': result['records_received'],
            'message': 'Data received and stored successfully',
        }
    except Exception as exc:  # pragma: no cover
        logger.exception('sync_ingest_failed source_ip=%s error=%s', source_ip, str(exc))
        raise HTTPException(status_code=500, detail='Internal ingest error')
