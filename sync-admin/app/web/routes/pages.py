from __future__ import annotations

import json
from math import ceil
from pathlib import Path
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.config.settings import settings
from app.core.db import get_db
from app.models.user import User
from app.repositories.sync_repository import SyncRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.control_service import ControlService
from app.services.dashboard_service import DashboardService
from app.services.export_service import audit_to_csv, records_to_csv
from app.services.user_service import UserService
from app.schemas.users import UserCreateRequest
from app.web.deps import require_web_role, require_web_user

router = APIRouter(tags=['web'])
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))


@router.get('/', response_class=HTMLResponse)
def root(request: Request):
    if request.session.get('user_id'):
        return RedirectResponse('/dashboard', status_code=status.HTTP_302_FOUND)
    return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)


@router.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, 'login.html', {'request': request, 'error': None})


@router.post('/login', response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    svc = AuthService(db)
    user = svc.login(username, password)
    if not user:
        return templates.TemplateResponse(
            request,
            'login.html',
            {'request': request, 'error': 'Credenciais inválidas'},
            status_code=400,
        )

    request.session['user_id'] = user.id
    request.session['username'] = user.username
    request.session['user_role'] = user.role
    return RedirectResponse('/dashboard', status_code=status.HTTP_302_FOUND)


@router.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)


@router.get('/dashboard', response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    svc = DashboardService(db)
    data = svc.summary()
    control = ControlService()
    control_summary = control.fetch_summary()
    job_summary = control.fetch_sync_jobs_summary()
    failed_batches, _ = SyncRepository(db).list_batches(page=1, page_size=10, status='failed')
    recent_errors = control.recent_agent_errors(limit=10)
    dead_letter_jobs = control.fetch_dead_letter_jobs(limit=10)
    for batch in failed_batches:
        recent_errors.append(
            {
                'timestamp': str(batch.received_at),
                'source': 'api',
                'event': 'failed_batch',
                'detail': batch.error_message or f'batch_id={batch.id}',
            }
        )
    recent_errors.append(control.api_error_snapshot())
    recent_errors = sorted(recent_errors, key=lambda x: x['timestamp'], reverse=True)[:15]
    chart_labels = [p['label'] for p in data['chart_daily']]
    chart_values = [p['value'] for p in data['chart_daily']]
    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            'request': request,
            'current_user': current_user,
            'summary': data,
            'control_summary': control_summary,
            'job_summary': job_summary,
            'recent_errors': recent_errors,
            'dead_letter_jobs': dead_letter_jobs,
            'chart_labels': json.dumps(chart_labels),
            'chart_values': json.dumps(chart_values),
        },
    )


@router.get('/dashboard/data')
def dashboard_data(_: object = Depends(require_web_user), db: Session = Depends(get_db)):
    svc = DashboardService(db)
    data = svc.summary()
    control_service = ControlService()
    control_summary = control_service.fetch_summary()
    job_summary = control_service.fetch_sync_jobs_summary()
    return JSONResponse(
        {
            'summary': {
                'total_records': data.get('total_records', 0),
                'last_received': str(data.get('last_received') or '-'),
                'failed_batches': data.get('failed_batches', 0),
                'api_status': data.get('api_status', 'unknown'),
            },
            'control': {
                'api_health': control_summary.api_health,
                'sync_batches_total': control_summary.sync_batches_total,
                'sync_records_inserted_total': control_summary.sync_records_inserted_total,
                'sync_records_updated_total': control_summary.sync_records_updated_total,
                'sync_application_failures_total': control_summary.sync_application_failures_total,
                'preflight_connection_errors_total': control_summary.preflight_connection_errors_total,
                'retention_processed_total': control_summary.retention_processed_total,
                'queue_pending_total': job_summary.pending_count,
                'queue_processing_total': job_summary.processing_count,
                'queue_dead_letter_total': job_summary.dead_letter_count,
                'queue_failed_total': job_summary.failed_count,
            },
        }
    )


@router.get('/records', response_class=HTMLResponse)
def records_page(
    request: Request,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    record_type: str | None = None,
    sort: str = 'created_at',
    current_user: User = Depends(require_web_role('admin', 'analyst')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    rows, total = repo.list_records(page=page, page_size=page_size, search=search, record_type=record_type, sort=sort)
    total_pages = max(1, ceil(total / page_size))
    return templates.TemplateResponse(
        request,
        'records.html',
        {
            'request': request,
            'current_user': current_user,
            'rows': rows,
            'page': page,
            'total': total,
            'total_pages': total_pages,
            'search': search or '',
            'record_type': record_type or '',
            'sort': sort,
        },
    )


@router.get('/records/export.csv')
def export_records_csv(
    request: Request,
    _: object = Depends(require_web_role('admin', 'analyst')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    rows, _ = repo.list_records(page=1, page_size=10000, search=None, record_type=None, sort='created_at')
    payload = [
        {
            'id': r.id,
            'batch_id': r.batch_id,
            'record_key': r.record_key,
            'record_type': r.record_type,
            'event_time': r.event_time,
            'created_at': r.created_at,
        }
        for r in rows
    ]
    csv_text = records_to_csv(payload)
    return Response(
        content=csv_text,
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=records.csv'},
    )


@router.get('/history', response_class=HTMLResponse)
def history_page(
    request: Request,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    current_user: User = Depends(require_web_role('admin', 'analyst')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    rows, total = repo.list_batches(page=page, page_size=page_size, status=status_filter)
    total_pages = max(1, ceil(total / page_size))
    return templates.TemplateResponse(
        request,
        'history.html',
        {
            'request': request,
            'current_user': current_user,
            'rows': rows,
            'page': page,
            'total': total,
            'total_pages': total_pages,
            'status_filter': status_filter or '',
        },
    )


@router.get('/settings', response_class=HTMLResponse)
def settings_page(
    request: Request,
    current_user: User = Depends(require_web_role('admin')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    user_service = UserService(UserRepository(db))
    summary = repo.dashboard_counts()
    control = ControlService()
    control_summary = control.fetch_summary()
    server_settings = None
    try:
        server_settings = control.get_server_settings()
    except Exception:
        server_settings = {
            'ingestion_enabled': True,
            'max_batch_size': 1000,
            'retention_mode': 'archive',
            'retention_months': 14,
        }
    flash = request.query_params.get('flash')
    error = request.query_params.get('error')
    generated_key = request.query_params.get('generated_key')
    return templates.TemplateResponse(
        request,
        'settings.html',
        {
            'request': request,
            'current_user': current_user,
            'summary': summary,
            'control_summary': control_summary,
            'flash': flash,
            'error': error,
            'generated_key': generated_key,
            'default_empresa_id': settings.control_empresa_id,
            'default_empresa_nome': settings.control_empresa_nome,
            'server_settings': server_settings,
            'users': user_service.list_users(),
        },
    )


@router.post('/settings/provision-tenant')
def settings_provision_tenant(
    request: Request,
    empresa_id: str = Form(...),
    nome: str = Form(...),
    _: object = Depends(require_web_role('admin')),
):
    control = ControlService()
    try:
        api_key = control.provision_tenant(empresa_id=empresa_id, nome=nome)
        key_file = control.update_agent_key_file(api_key)
        return RedirectResponse(
            f'/settings?flash=Tenant+provisionado+e+chave+aplicada+no+agente+({key_file})&generated_key={api_key}',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+provisionar+tenant:+{str(exc)}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/rotate-tenant-key')
def settings_rotate_tenant_key(
    request: Request,
    empresa_id: str = Form(...),
    _: object = Depends(require_web_role('admin')),
):
    control = ControlService()
    try:
        api_key = control.rotate_tenant_key(empresa_id=empresa_id)
        key_file = control.update_agent_key_file(api_key)
        return RedirectResponse(
            f'/settings?flash=Chave+rotacionada+e+aplicada+no+agente+({key_file})&generated_key={api_key}',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+rotacionar+chave:+{str(exc)}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/server-settings')
def settings_server_settings(
    request: Request,
    ingestion_enabled: str = Form(...),
    max_batch_size: int = Form(...),
    retention_mode: str = Form(...),
    retention_months: int = Form(...),
    _: object = Depends(require_web_role('admin')),
):
    control = ControlService()
    try:
        control.update_server_settings(
            ingestion_enabled=ingestion_enabled.lower() == 'true',
            max_batch_size=max_batch_size,
            retention_mode=retention_mode,
            retention_months=retention_months,
        )
        return RedirectResponse(
            '/settings?flash=Configuracoes+de+servidor+atualizadas',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+atualizar+configuracoes+de+servidor:+{str(exc)}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/dashboard/jobs/{job_id}/retry')
def dashboard_retry_job(
    request: Request,
    job_id: str,
    _: object = Depends(require_web_role('admin')),
):
    control = ControlService()
    try:
        control.retry_sync_job(job_id)
        return RedirectResponse(
            '/dashboard?flash=Job+reenfileirado+com+sucesso',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/dashboard?error=Falha+ao+reenfileirar+job:+{str(exc)}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/users')
def settings_create_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form('viewer'),
    _: object = Depends(require_web_role('admin')),
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))
    try:
        service.create_user(UserCreateRequest(username=username, full_name=full_name, password=password, role=role))
        return RedirectResponse('/settings?flash=Usuario+criado+com+sucesso', status_code=status.HTTP_302_FOUND)
    except (HTTPException, ValidationError) as exc:
        detail = quote_plus(str(getattr(exc, 'detail', exc)))
        return RedirectResponse(f'/settings?error={detail}', status_code=status.HTTP_302_FOUND)


@router.get('/dashboard/audit.csv')
def export_dashboard_audit_csv(
    request: Request,
    _: object = Depends(require_web_role('admin')),
    db: Session = Depends(get_db),
):
    control = ControlService()
    failed_batches, _ = SyncRepository(db).list_batches(page=1, page_size=100, status='failed')
    rows = control.recent_agent_errors(limit=100)
    for batch in failed_batches:
        rows.append(
            {
                'timestamp': str(batch.received_at),
                'source': 'api',
                'event': 'failed_batch',
                'detail': batch.error_message or f'batch_id={batch.id}',
            }
        )
    rows.append(control.api_error_snapshot())
    csv_text = audit_to_csv(rows)
    return Response(
        content=csv_text,
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_dashboard.csv'},
    )
