from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.config.settings import settings
from app.core.db import SessionLocal

router = APIRouter(tags=['health'])


@router.get('/health')
def health():
    return {'status': 'online', 'service': 'sync-admin'}


@router.get('/health/live')
def liveness():
    return {'status': 'live', 'service': 'sync-admin'}


@router.get('/health/ready')
def readiness():
    details = {
        'database': 'unknown',
        'control_api': 'unknown',
    }

    try:
        with SessionLocal() as db:
            db.execute(text('SELECT 1'))
        details['database'] = 'ready'
    except Exception:
        details['database'] = 'error'

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.control_api_base_url.rstrip('/')}/health/ready")
            if response.status_code == 200:
                details['control_api'] = 'ready'
            else:
                details['control_api'] = f"error:{response.status_code}"
    except Exception:
        details['control_api'] = 'error'

    if not all(value == 'ready' for value in details.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={'status': 'not_ready', 'components': details},
        )

    return {'status': 'ready', 'components': details}
