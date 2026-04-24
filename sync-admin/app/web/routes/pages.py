from __future__ import annotations

from datetime import date, timedelta
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
from app.core.audit import build_request_audit_context
from app.core.db import get_db
from app.models.user import User
from app.repositories.admin_user_audit_log_repository import AdminUserAuditLogRepository
from app.repositories.user_branch_permission_repository import UserBranchPermissionRepository
from app.repositories.sync_repository import SyncRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.client_scope_service import ClientScopeService
from app.services.control_service import ControlService, SourceCycleSummary, SyncJobsSummary, TenantObservabilitySummary
from app.services.dashboard_service import DashboardService
from app.services.export_service import (
    audit_to_csv,
    audit_to_markdown,
    audit_to_pdf_bytes,
    audit_to_xlsx_bytes,
    records_to_csv,
    records_to_pdf_bytes,
    records_to_xlsx_bytes,
    report_recent_sales_to_csv,
    report_to_pdf_bytes,
    report_to_xlsx_bytes,
    write_markdown_snapshot,
)
from app.services.user_service import UserService
from app.schemas.users import UserCreateRequest, UserUpdateRequest
from app.web.deps import require_client_user, require_web_permission

router = APIRouter(tags=['web'])
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))

_LOCAL_AUDIT_FIELD_LABELS = {
    'full_name': 'Nome',
    'role': 'Perfil',
    'empresa_id': 'Empresa',
    'scope_type': 'Escopo',
    'allowed_branch_codes': 'Filiais',
    'is_active': 'Ativo',
}

_LOCAL_AUDIT_VALUE_LABELS = {
    'scope_type': {
        'company': 'empresa inteira',
        'branch_set': 'filiais especificas',
    }
}

_LOCAL_AUDIT_SEVERITY_LABELS = {
    'critical': 'critico',
    'warning': 'atencao',
    'info': 'informativo',
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _format_local_user_audit_value(field: str, value: object) -> str:
    if isinstance(value, list):
        return ', '.join(str(item) for item in value) if value else '-'
    if isinstance(value, bool):
        return 'sim' if value else 'nao'
    if value in (None, ''):
        return '-'
    mapped_value = _LOCAL_AUDIT_VALUE_LABELS.get(field, {}).get(value)
    if mapped_value:
        return mapped_value
    return str(value)


def _build_local_user_audit_summary(detail: dict[str, object]) -> list[dict[str, str]]:
    before = detail.get('before') if isinstance(detail.get('before'), dict) else None
    after = detail.get('after') if isinstance(detail.get('after'), dict) else None
    fields_order = (
        'full_name',
        'role',
        'empresa_id',
        'scope_type',
        'allowed_branch_codes',
        'is_active',
    )
    summary: list[dict[str, str]] = []

    if before and after:
        for field in fields_order:
            before_value = before.get(field)
            after_value = after.get(field)
            if before_value == after_value:
                continue
            summary.append(
                {
                    'label': _LOCAL_AUDIT_FIELD_LABELS.get(field, field),
                    'before': _format_local_user_audit_value(field, before_value),
                    'after': _format_local_user_audit_value(field, after_value),
                    'field': field,
                }
            )
        return summary

    if after:
        for field in fields_order:
            after_value = after.get(field)
            formatted_after = _format_local_user_audit_value(field, after_value)
            if formatted_after == '-':
                continue
            summary.append(
                {
                    'label': _LOCAL_AUDIT_FIELD_LABELS.get(field, field),
                    'before': '-',
                    'after': formatted_after,
                    'field': field,
                }
            )
    return summary


def _build_local_user_audit_visual_state(
    *,
    action: str,
    detail: dict[str, object],
    detail_summary: list[dict[str, str]],
) -> dict[str, object]:
    before = detail.get('before') if isinstance(detail.get('before'), dict) else {}
    after = detail.get('after') if isinstance(detail.get('after'), dict) else {}
    before_branches = set(before.get('allowed_branch_codes') or [])
    after_branches = set(after.get('allowed_branch_codes') or [])

    signals: list[str] = []
    severity = 'info'

    if action == 'user.create':
        signals.append('Novo usuario criado')

    if before.get('empresa_id') != after.get('empresa_id') and before.get('empresa_id') is not None:
        severity = 'critical'
        signals.append('Empresa vinculada alterada')

    if before.get('role') != after.get('role') and before.get('role') is not None:
        severity = 'critical'
        signals.append('Perfil alterado')

    if before.get('is_active') is True and after.get('is_active') is False:
        severity = 'warning' if severity != 'critical' else severity
        signals.append('Usuario desativado')

    if before.get('scope_type') != after.get('scope_type') and before.get('scope_type') is not None:
        severity = 'warning' if severity != 'critical' else severity
        signals.append('Escopo de acesso alterado')

    removed_branches = sorted(before_branches - after_branches)
    if removed_branches:
        severity = 'warning' if severity != 'critical' else severity
        signals.append(f"Filiais removidas: {', '.join(removed_branches)}")

    if detail_summary and not signals:
        signals.append('Campos administrativos atualizados')

    if not detail_summary and not signals:
        signals.append('Sem diff estruturado')

    return {
        'severity': severity,
        'severity_label': _LOCAL_AUDIT_SEVERITY_LABELS[severity],
        'signals': signals,
    }


def _compute_previous_period(start_date: str | None, end_date: str | None) -> tuple[str, str] | None:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if not start or not end or end < start:
        return None
    delta_days = (end - start).days
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=delta_days)
    return previous_start.isoformat(), previous_end.isoformat()


def _safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_signed(value: float, decimals: int = 2) -> str:
    return f'{value:+.{decimals}f}'


def _format_decimal(value: float, decimals: int = 2) -> str:
    return f'{value:.{decimals}f}'


def _build_filter_chips(
    *,
    start_date: str | None,
    end_date: str | None,
    branch_code: str | None,
    terminal_code: str | None,
    top_limit: int,
    recent_limit: int,
) -> list[dict[str, str]]:
    period_value = 'Todo o periodo'
    if start_date and end_date:
        period_value = f'{start_date} ate {end_date}'
    elif start_date:
        period_value = f'A partir de {start_date}'
    elif end_date:
        period_value = f'Ate {end_date}'

    return [
        {'label': 'Periodo', 'value': period_value},
        {'label': 'Filial', 'value': branch_code or 'Todas'},
        {'label': 'Terminal', 'value': terminal_code or 'Todos'},
        {'label': 'Top produtos', 'value': str(top_limit)},
        {'label': 'Vendas recentes', 'value': str(recent_limit)},
    ]


def _build_report_highlights(
    *,
    overview: dict,
    daily_items: list[dict],
    top_items: list[dict],
) -> list[dict[str, str]]:
    total_records = int(overview.get('total_records', 0) or 0)
    total_sales_value = _safe_float(overview.get('total_sales_value'))
    active_days = len(daily_items)
    average_ticket = total_sales_value / total_records if total_records else 0.0
    average_daily_sales = total_sales_value / active_days if active_days else 0.0

    best_day = None
    if daily_items:
        best_day = max(daily_items, key=lambda item: _safe_float(item.get('total_sales_value')))

    best_product = None
    if top_items:
        best_product = max(top_items, key=lambda item: _safe_float(item.get('total_sales_value')))

    leader_share = 0.0
    if best_product and total_sales_value > 0:
        leader_share = (_safe_float(best_product.get('total_sales_value')) / total_sales_value) * 100

    return [
        {
            'label': 'Ticket medio',
            'value': _format_decimal(average_ticket),
            'hint': 'Valor medio por registro no periodo filtrado.',
        },
        {
            'label': 'Media diaria',
            'value': _format_decimal(average_daily_sales),
            'hint': f'{active_days} dia(s) com movimentacao capturada.',
        },
        {
            'label': 'Melhor dia',
            'value': best_day.get('day', '-') if best_day else '-',
            'hint': (
                f"Valor {_format_decimal(_safe_float(best_day.get('total_sales_value')))}"
                if best_day
                else 'Sem serie diaria para o filtro atual.'
            ),
        },
        {
            'label': 'Produto lider',
            'value': best_product.get('produto', '-') if best_product else '-',
            'hint': (
                f'{leader_share:.1f}% do valor total no periodo.'
                if best_product
                else 'Sem produtos ranqueados para o filtro atual.'
            ),
        },
    ]


def _build_comparison(
    *,
    current_overview: dict,
    previous_overview: dict | None,
    previous_period: tuple[str, str] | None,
) -> dict | None:
    if not previous_overview or not previous_period:
        return None
    current_records = int(current_overview.get('total_records', 0) or 0)
    previous_records = int(previous_overview.get('total_records', 0) or 0)
    current_value = _safe_float(current_overview.get('total_sales_value'))
    previous_value = _safe_float(previous_overview.get('total_sales_value'))
    records_pct = ((current_records - previous_records) / previous_records * 100) if previous_records else None
    value_pct = ((current_value - previous_value) / previous_value * 100) if previous_value else None
    return {
        'previous_start_date': previous_period[0],
        'previous_end_date': previous_period[1],
        'previous_total_records': previous_records,
        'previous_total_sales_value': f'{previous_value:.2f}',
        'delta_total_records': current_records - previous_records,
        'delta_total_sales_value': _format_signed(current_value - previous_value),
        'delta_total_records_pct': None if records_pct is None else _format_signed(records_pct, decimals=1),
        'delta_total_sales_value_pct': None if value_pct is None else _format_signed(value_pct, decimals=1),
    }


def _build_report_payload(
    *,
    empresa_id: str | None,
    start_date: str | None,
    end_date: str | None,
    branch_code: str | None,
    terminal_code: str | None,
    top_limit: int,
    recent_limit: int,
) -> dict:
    control = ControlService()
    normalized_top_limit = max(1, min(top_limit, 20))
    normalized_recent_limit = max(1, min(recent_limit, 50))
    overview = control.fetch_report_overview(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    daily_sales = control.fetch_report_daily_sales(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    top_products = control.fetch_report_top_products(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        limit=normalized_top_limit,
    )
    recent_sales = control.fetch_report_recent_sales(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        limit=normalized_recent_limit,
    )
    daily_items = list(daily_sales.get('items', []))
    top_items = list(top_products.get('items', []))
    recent_items = list(recent_sales.get('items', []))
    previous_period = _compute_previous_period(start_date, end_date)
    previous_overview = None
    if previous_period:
        previous_overview = control.fetch_report_overview(
            empresa_id=empresa_id,
            start_date=previous_period[0],
            end_date=previous_period[1],
            branch_code=branch_code,
            terminal_code=terminal_code,
        )
    comparison = _build_comparison(
        current_overview=overview,
        previous_overview=previous_overview,
        previous_period=previous_period,
    )
    highlight_cards = _build_report_highlights(
        overview=overview,
        daily_items=daily_items,
        top_items=top_items,
    )
    filter_chips = _build_filter_chips(
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        top_limit=normalized_top_limit,
        recent_limit=normalized_recent_limit,
    )
    return {
        'overview': overview,
        'daily_items': daily_items,
        'top_items': top_items,
        'recent_items': recent_items,
        'comparison': comparison,
        'highlight_cards': highlight_cards,
        'filter_chips': filter_chips,
        'start_date': start_date or '',
        'end_date': end_date or '',
        'branch_code': branch_code or '',
        'terminal_code': terminal_code or '',
        'top_limit': normalized_top_limit,
        'recent_limit': normalized_recent_limit,
        'daily_chart_labels': json.dumps([item.get('day', '-') for item in daily_items]),
        'daily_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in daily_items]
        ),
        'top_chart_labels': json.dumps([item.get('produto', '-') for item in top_items]),
        'top_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in top_items]
        ),
    }


@router.get('/', response_class=HTMLResponse)
def root(request: Request):
    if request.session.get('user_id'):
        if request.session.get('user_role') == 'client':
            return RedirectResponse('/client/dashboard', status_code=status.HTTP_302_FOUND)
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
    request.session['empresa_id'] = user.empresa_id
    if user.role == 'client':
        return RedirectResponse('/client/dashboard', status_code=status.HTTP_302_FOUND)
    return RedirectResponse('/dashboard', status_code=status.HTTP_302_FOUND)


@router.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)


@router.get('/dashboard', response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: User = Depends(require_web_permission('dashboard.view')),
    db: Session = Depends(get_db),
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
):
    svc = DashboardService(db)
    data = svc.summary(
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    control = ControlService()
    control_summary = control.fetch_summary()
    control_online = control_summary.api_health == 'online'
    if control_online:
        job_summary = control.fetch_sync_jobs_summary()
        tenant_observability = control.fetch_tenant_observability()
        source_configs = control.fetch_source_configs()
        source_cycle_summary = control.fetch_source_cycle_summary(source_configs)
        destination_configs = control.fetch_destination_configs()
    else:
        empresa_id = settings.control_empresa_id
        job_summary = SyncJobsSummary(
            empresa_id=empresa_id,
            pending_count=0.0,
            processing_count=0.0,
            done_count=0.0,
            dead_letter_count=0.0,
            failed_count=0.0,
        )
        tenant_observability = TenantObservabilitySummary(
            empresa_id=empresa_id,
            sync_batches_total=0.0,
            sync_failures_total=0.0,
            tenant_scheduler_runs_total=0.0,
            tenant_queue_processed_total=0.0,
            tenant_queue_failed_total=0.0,
            tenant_queue_retried_total=0.0,
            tenant_queue_dead_letter_total=0.0,
            tenant_destination_delivery_total=0.0,
            tenant_destination_delivery_failed_total=0.0,
            sync_last_success_lag_seconds=0.0,
            tenant_scheduler_last_success_lag_seconds=0.0,
            tenant_queue_last_event_lag_seconds=0.0,
            tenant_destination_last_event_lag_seconds=0.0,
        )
        source_configs = []
        source_cycle_summary = SourceCycleSummary(
            empresa_id=empresa_id,
            total_count=0,
            active_count=0,
            due_count=0,
            overdue_count=0,
            next_run_at='-',
            last_success_at='-',
            last_success_lag_seconds=0.0,
        )
        destination_configs = []
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
    recent_errors.append(
        control.api_error_snapshot()
        if control_online
        else {
            'timestamp': '-',
            'source': 'api',
            'event': 'control_api_offline',
            'detail': f'api_health={control_summary.api_health}',
        }
    )
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
            'tenant_observability': tenant_observability,
            'source_configs': source_configs,
            'source_cycle_summary': source_cycle_summary,
            'destination_configs': destination_configs,
            'recent_errors': recent_errors,
            'dead_letter_jobs': dead_letter_jobs,
            'chart_labels': json.dumps(chart_labels),
            'chart_values': json.dumps(chart_values),
            'company_code': company_code or '',
            'branch_code': branch_code or '',
            'terminal_code': terminal_code or '',
        },
    )


@router.get('/dashboard/data')
def dashboard_data(
    _: object = Depends(require_web_permission('dashboard.view')),
    db: Session = Depends(get_db),
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
):
    svc = DashboardService(db)
    data = svc.summary(
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    control_service = ControlService()
    control_summary = control_service.fetch_summary()
    control_online = control_summary.api_health == 'online'
    if control_online:
        job_summary = control_service.fetch_sync_jobs_summary()
        tenant_observability = control_service.fetch_tenant_observability()
        source_configs = control_service.fetch_source_configs()
        source_cycle_summary = control_service.fetch_source_cycle_summary(source_configs)
        destination_configs = control_service.fetch_destination_configs()
    else:
        empresa_id = settings.control_empresa_id
        job_summary = SyncJobsSummary(
            empresa_id=empresa_id,
            pending_count=0.0,
            processing_count=0.0,
            done_count=0.0,
            dead_letter_count=0.0,
            failed_count=0.0,
        )
        tenant_observability = TenantObservabilitySummary(
            empresa_id=empresa_id,
            sync_batches_total=0.0,
            sync_failures_total=0.0,
            tenant_scheduler_runs_total=0.0,
            tenant_queue_processed_total=0.0,
            tenant_queue_failed_total=0.0,
            tenant_queue_retried_total=0.0,
            tenant_queue_dead_letter_total=0.0,
            tenant_destination_delivery_total=0.0,
            tenant_destination_delivery_failed_total=0.0,
            sync_last_success_lag_seconds=0.0,
            tenant_scheduler_last_success_lag_seconds=0.0,
            tenant_queue_last_event_lag_seconds=0.0,
            tenant_destination_last_event_lag_seconds=0.0,
        )
        source_configs = []
        source_cycle_summary = SourceCycleSummary(
            empresa_id=empresa_id,
            total_count=0,
            active_count=0,
            due_count=0,
            overdue_count=0,
            next_run_at='-',
            last_success_at='-',
            last_success_lag_seconds=0.0,
        )
        destination_configs = []
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
                'destination_delivery_total': control_summary.tenant_destination_delivery_total,
                'destination_delivery_failed_total': control_summary.tenant_destination_delivery_failed_total,
            },
            'tenant_observability': {
                'empresa_id': tenant_observability.empresa_id,
                'sync_batches_total': tenant_observability.sync_batches_total,
                'sync_failures_total': tenant_observability.sync_failures_total,
                'tenant_scheduler_runs_total': tenant_observability.tenant_scheduler_runs_total,
                'tenant_queue_processed_total': tenant_observability.tenant_queue_processed_total,
                'tenant_queue_failed_total': tenant_observability.tenant_queue_failed_total,
                'tenant_queue_retried_total': tenant_observability.tenant_queue_retried_total,
                'tenant_queue_dead_letter_total': tenant_observability.tenant_queue_dead_letter_total,
                'tenant_destination_delivery_total': tenant_observability.tenant_destination_delivery_total,
                'tenant_destination_delivery_failed_total': tenant_observability.tenant_destination_delivery_failed_total,
                'sync_last_success_lag_seconds': tenant_observability.sync_last_success_lag_seconds,
                'tenant_scheduler_last_success_lag_seconds': tenant_observability.tenant_scheduler_last_success_lag_seconds,
                'tenant_queue_last_event_lag_seconds': tenant_observability.tenant_queue_last_event_lag_seconds,
                'tenant_destination_last_event_lag_seconds': tenant_observability.tenant_destination_last_event_lag_seconds,
            },
            'source_cycle': {
                'empresa_id': source_cycle_summary.empresa_id,
                'total_count': source_cycle_summary.total_count,
                'active_count': source_cycle_summary.active_count,
                'due_count': source_cycle_summary.due_count,
                'overdue_count': source_cycle_summary.overdue_count,
                'next_run_at': source_cycle_summary.next_run_at,
                'last_success_at': source_cycle_summary.last_success_at,
                'last_success_lag_seconds': source_cycle_summary.last_success_lag_seconds,
            },
            'destinations': destination_configs,
            'source_configs': source_configs,
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
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    current_user: User = Depends(require_web_permission('records.view')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    rows, total = repo.list_records(
        page=page,
        page_size=page_size,
        search=search,
        record_type=record_type,
        sort=sort,
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
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
            'company_code': company_code or '',
            'branch_code': branch_code or '',
            'terminal_code': terminal_code or '',
        },
    )


@router.get('/reports', response_class=HTMLResponse)
def reports_page(
    request: Request,
    empresa_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
    current_user: User = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    return templates.TemplateResponse(
        request,
        'reports.html',
        {
            'request': request,
            'current_user': current_user,
            'selected_empresa_id': empresa_id or settings.control_empresa_id,
            **payload,
        },
    )


@router.get('/client/dashboard', response_class=HTMLResponse)
def client_dashboard_page(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    current_user: User = Depends(require_client_user),
    db: Session = Depends(get_db),
):
    scope = ClientScopeService(
        ControlService(),
        UserBranchPermissionRepository(db),
    ).resolve(
        user=current_user,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    control = ControlService()
    overview = control.fetch_report_overview(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
    )
    recent_sales = control.fetch_report_recent_sales(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        limit=10,
    )
    return templates.TemplateResponse(
        request,
        'client_dashboard.html',
        {
            'request': request,
            'current_user': current_user,
            'overview': overview,
            'recent_items': list(recent_sales.get('items', [])),
            'allowed_branch_codes': scope.allowed_branch_codes,
            'start_date': start_date or '',
            'end_date': end_date or '',
            'branch_code': scope.selected_branch_code or '',
            'terminal_code': terminal_code or '',
        },
    )


@router.get('/client/reports', response_class=HTMLResponse)
def client_reports_page(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
    current_user: User = Depends(require_client_user),
    db: Session = Depends(get_db),
):
    scope = ClientScopeService(
        ControlService(),
        UserBranchPermissionRepository(db),
    ).resolve(
        user=current_user,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    return templates.TemplateResponse(
        request,
        'client_reports.html',
        {
            'request': request,
            'current_user': current_user,
            'allowed_branch_codes': scope.allowed_branch_codes,
            'branch_code': scope.selected_branch_code or '',
            **payload,
        },
    )


@router.get('/reports/export.csv')
def export_reports_csv(
    empresa_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    recent_limit: int = 50,
    _: object = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        top_limit=10,
        recent_limit=recent_limit,
    )
    csv_text = report_recent_sales_to_csv(payload['recent_items'])
    return Response(
        content=csv_text,
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=reports.csv'},
    )


@router.get('/reports/export.xlsx')
def export_reports_xlsx(
    empresa_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    _: object = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    xlsx_bytes = report_to_xlsx_bytes(
        payload['overview'],
        payload['daily_items'],
        payload['top_items'],
        payload['recent_items'],
    )
    return Response(
        content=xlsx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=reports.xlsx'},
    )


@router.get('/reports/export.pdf')
def export_reports_pdf(
    empresa_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    _: object = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    pdf_bytes = report_to_pdf_bytes(
        payload['overview'],
        payload['daily_items'],
        payload['top_items'],
        payload['recent_items'],
        title='Relatorios administrativos',
    )
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=reports.pdf'},
    )


@router.get('/client/reports/export.csv')
def export_client_reports_csv(
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    recent_limit: int = 50,
    current_user: User = Depends(require_client_user),
    db: Session = Depends(get_db),
):
    scope = ClientScopeService(
        ControlService(),
        UserBranchPermissionRepository(db),
    ).resolve(
        user=current_user,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        top_limit=10,
        recent_limit=recent_limit,
    )
    csv_text = report_recent_sales_to_csv(payload['recent_items'])
    return Response(
        content=csv_text,
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=client_reports.csv'},
    )


@router.get('/client/reports/export.xlsx')
def export_client_reports_xlsx(
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    current_user: User = Depends(require_client_user),
    db: Session = Depends(get_db),
):
    scope = ClientScopeService(
        ControlService(),
        UserBranchPermissionRepository(db),
    ).resolve(
        user=current_user,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    xlsx_bytes = report_to_xlsx_bytes(
        payload['overview'],
        payload['daily_items'],
        payload['top_items'],
        payload['recent_items'],
    )
    return Response(
        content=xlsx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=client_reports.xlsx'},
    )


@router.get('/client/reports/export.pdf')
def export_client_reports_pdf(
    start_date: str | None = None,
    end_date: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    current_user: User = Depends(require_client_user),
    db: Session = Depends(get_db),
):
    scope = ClientScopeService(
        ControlService(),
        UserBranchPermissionRepository(db),
    ).resolve(
        user=current_user,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    pdf_bytes = report_to_pdf_bytes(
        payload['overview'],
        payload['daily_items'],
        payload['top_items'],
        payload['recent_items'],
        title='Relatorios do cliente',
    )
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=client_reports.pdf'},
    )


@router.get('/records/export.csv')
def export_records_csv(
    _: object = Depends(require_web_permission('records.view')),
    db: Session = Depends(get_db),
    search: str | None = None,
    record_type: str | None = None,
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
):
    repo = SyncRepository(db)
    rows, _ = repo.list_records(
        page=1,
        page_size=10000,
        search=search,
        record_type=record_type,
        sort='created_at',
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
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


@router.get('/records/export.xlsx')
def export_records_xlsx(
    _: object = Depends(require_web_permission('records.view')),
    db: Session = Depends(get_db),
    search: str | None = None,
    record_type: str | None = None,
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
):
    repo = SyncRepository(db)
    rows, _ = repo.list_records(
        page=1,
        page_size=10000,
        search=search,
        record_type=record_type,
        sort='created_at',
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
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
    xlsx_bytes = records_to_xlsx_bytes(payload)
    return Response(
        content=xlsx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=records.xlsx'},
    )


@router.get('/records/export.pdf')
def export_records_pdf(
    _: object = Depends(require_web_permission('records.view')),
    db: Session = Depends(get_db),
    search: str | None = None,
    record_type: str | None = None,
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
):
    repo = SyncRepository(db)
    rows, _ = repo.list_records(
        page=1,
        page_size=10000,
        search=search,
        record_type=record_type,
        sort='created_at',
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
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
    pdf_bytes = records_to_pdf_bytes(payload)
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=records.pdf'},
    )


@router.get('/history', response_class=HTMLResponse)
def history_page(
    request: Request,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    current_user: User = Depends(require_web_permission('history.view')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    rows, total = repo.list_batches(
        page=page,
        page_size=page_size,
        status=status_filter,
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
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
            'company_code': company_code or '',
            'branch_code': branch_code or '',
            'terminal_code': terminal_code or '',
        },
    )


@router.get('/connected-apis', response_class=HTMLResponse)
def connected_apis_page(
    request: Request,
    empresa_id: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    current_user: User = Depends(require_web_permission('remote_clients.view')),
):
    control = ControlService()
    fleet_summary = control.fetch_remote_client_summary(
        empresa_id=empresa_id,
        status=status_filter,
        search=search,
    )
    clients = control.fetch_remote_clients(
        empresa_id=empresa_id,
        status=status_filter,
        search=search,
    )
    return templates.TemplateResponse(
        request,
        'connected_apis.html',
        {
            'request': request,
            'current_user': current_user,
            'fleet_summary': fleet_summary,
            'clients': clients,
            'empresa_id': empresa_id or '',
            'status_filter': status_filter or '',
            'search': search or '',
        },
    )


@router.get('/connected-apis/{client_id}', response_class=HTMLResponse)
def connected_api_detail_page(
    request: Request,
    client_id: str,
    current_user: User = Depends(require_web_permission('remote_clients.view')),
):
    control = ControlService()
    client_data = control.fetch_remote_client(client_id)
    logs = control.fetch_remote_client_logs(client_id, limit=20)
    return templates.TemplateResponse(
        request,
        'connected_api_detail.html',
        {
            'request': request,
            'current_user': current_user,
            'client_data': client_data,
            'logs': logs,
            'pretty_config_snapshot': json.dumps(client_data.get('config_snapshot', {}), indent=2, ensure_ascii=False),
            'pretty_status_snapshot': json.dumps(client_data.get('status_snapshot', {}), indent=2, ensure_ascii=False),
        },
    )


@router.post('/connected-apis/{client_id}/sync')
def connected_api_force_sync(
    client_id: str,
    current_user: User = Depends(require_web_permission('remote_clients.manage')),
):
    control = ControlService()
    try:
        control.queue_remote_force_sync(client_id, actor=current_user.username)
        return RedirectResponse(
            f'/connected-apis/{client_id}?flash=Sincronizacao+remota+enfileirada',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/connected-apis/{client_id}?error={quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/connected-apis/{client_id}/config')
def connected_api_update_config(
    client_id: str,
    config_payload: str = Form(...),
    current_user: User = Depends(require_web_permission('remote_clients.manage')),
):
    control = ControlService()
    try:
        payload = json.loads(config_payload)
        if not isinstance(payload, dict):
            raise ValueError('Config payload deve ser um objeto JSON.')
        control.queue_remote_config_update(client_id, payload=payload, actor=current_user.username)
        return RedirectResponse(
            f'/connected-apis/{client_id}?flash=Atualizacao+de+configuracao+enfileirada',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/connected-apis/{client_id}?error={quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.get('/settings', response_class=HTMLResponse)
def settings_page(
    request: Request,
    current_user: User = Depends(require_web_permission('settings.view')),
    db: Session = Depends(get_db),
):
    repo = SyncRepository(db)
    user_service = UserService(UserRepository(db))
    local_user_audit_events = []
    for item in AdminUserAuditLogRepository(db).list_recent(limit=10):
        detail = json.loads(item.detail_json or '{}')
        detail_summary = _build_local_user_audit_summary(detail)
        visual_state = _build_local_user_audit_visual_state(
            action=item.action,
            detail=detail,
            detail_summary=detail_summary,
        )
        local_user_audit_events.append(
            {
                'id': item.id,
                'actor': item.actor,
                'action': item.action,
                'target_username': item.target_username,
                'status': item.status,
                'correlation_id': item.correlation_id or '-',
                'request_path': item.request_path or '-',
                'actor_ip': item.actor_ip or '-',
                'user_agent': item.user_agent or '-',
                'detail': detail,
                'detail_summary': detail_summary,
                'detail_raw': json.dumps(detail, ensure_ascii=False, sort_keys=True),
                'severity': visual_state['severity'],
                'severity_label': visual_state['severity_label'],
                'signals': visual_state['signals'],
                'created_at': item.created_at,
            }
        )
    summary = repo.dashboard_counts()
    control = ControlService()
    control_summary = control.fetch_summary()
    source_configs = control.fetch_source_configs()
    destination_configs = control.fetch_destination_configs()
    audit_summary = control.fetch_audit_summary()
    audit_events = control.fetch_audit_events(limit=10)
    server_settings = None
    try:
        server_settings = control.get_server_settings()
    except Exception:
        server_settings = {
            'ingestion_enabled': True,
            'max_batch_size': 1000,
            'retention_mode': 'archive',
            'retention_months': 14,
            'connection_secrets_file': 'output/tenant_connection_secrets.json',
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
            'local_user_audit_events': local_user_audit_events,
            'source_configs': source_configs,
            'destination_configs': destination_configs,
            'audit_summary': audit_summary,
            'audit_events': audit_events,
        },
    )


@router.get('/settings/company-branches')
def settings_company_branches(
    empresa_id: str,
    _: object = Depends(require_web_permission('settings.view')),
):
    branch_codes = ControlService().fetch_report_branch_options(empresa_id=empresa_id)
    return JSONResponse({'empresa_id': empresa_id, 'items': branch_codes})


@router.post('/settings/provision-tenant')
def settings_provision_tenant(
    request: Request,
    empresa_id: str = Form(...),
    nome: str = Form(...),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        result = control.provision_tenant(empresa_id=empresa_id, nome=nome, actor=current_user.username)
        api_key = str(result['api_key'])
        key_file = control.update_agent_key_file(api_key)
        expires_at = quote_plus(str(result.get('api_key_expires_at') or '-'))
        return RedirectResponse(
            (
                f'/settings?flash=Tenant+provisionado+e+chave+aplicada+no+agente+({key_file})'
                f'+-+expira+em+{expires_at}&generated_key={api_key}&generated_key_expires_at={expires_at}'
            ),
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
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        result = control.rotate_tenant_key(empresa_id=empresa_id, actor=current_user.username)
        api_key = str(result['api_key'])
        key_file = control.update_agent_key_file(api_key)
        expires_at = quote_plus(str(result.get('api_key_expires_at') or '-'))
        return RedirectResponse(
            (
                f'/settings?flash=Chave+rotacionada+e+aplicada+no+agente+({key_file})'
                f'+-+expira+em+{expires_at}&generated_key={api_key}&generated_key_expires_at={expires_at}'
            ),
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+rotacionar+chave:+{str(exc)}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/dashboard/source-configs/{config_id}/sync')
def dashboard_trigger_source_sync(
    config_id: str,
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        control.trigger_source_sync(
            config_id,
            empresa_id=settings.control_empresa_id,
            actor=current_user.username,
        )
        return RedirectResponse(
            '/dashboard?flash=Sincronizacao+da+fonte+enfileirada',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/dashboard?error=Falha+ao+enfileirar+sincronizacao:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/dashboard/source-configs/sync-all')
def dashboard_trigger_all_source_sync(
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        result = control.trigger_all_source_sync(
            empresa_id=settings.control_empresa_id,
            actor=current_user.username,
        )
        return RedirectResponse(
            f"/dashboard?flash=Sincronizacao+de+{result['active_count']}+fontes+ativas+enfileiradas",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/dashboard?error=Falha+ao+enfileirar+sincronizacao+em+lote:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/server-settings')
def settings_server_settings(
    request: Request,
    ingestion_enabled: str = Form(...),
    max_batch_size: int = Form(...),
    retention_mode: str = Form(...),
    retention_months: int = Form(...),
    connection_secrets_file: str = Form(...),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        control.update_server_settings(
            ingestion_enabled=ingestion_enabled.lower() == 'true',
            max_batch_size=max_batch_size,
            retention_mode=retention_mode,
            retention_months=retention_months,
            connection_secrets_file=connection_secrets_file,
            actor=current_user.username,
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


@router.post('/settings/secure-connection-config')
def settings_secure_connection_config(
    request: Request,
    scope: str = Form(...),
    nome: str = Form(...),
    connector_type: str = Form(...),
    sync_interval_minutes: int = Form(15),
    settings_json: str = Form('{}'),
    secret_settings_json: str = Form('{}'),
    generate_access_key: str = Form('false'),
    access_key_field: str = Form('api_key'),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        settings_payload = json.loads(settings_json or '{}')
        secret_settings_payload = json.loads(secret_settings_json or '{}')
        if not isinstance(settings_payload, dict) or not isinstance(secret_settings_payload, dict):
            raise ValueError('Payloads de configuracao devem ser objetos JSON.')
        result = control.create_secure_connection_config(
            scope=scope,
            nome=nome,
            connector_type=connector_type,
            sync_interval_minutes=sync_interval_minutes,
            settings={str(key): str(value) for key, value in settings_payload.items()},
            secret_settings={str(key): str(value) for key, value in secret_settings_payload.items()},
            generate_access_key=generate_access_key.lower() == 'true',
            access_key_field=access_key_field or None,
            actor=current_user.username,
        )
        generated_key = quote_plus(str(result.get('generated_access_key') or ''))
        flash = quote_plus(f"Servidor seguro criado com referencia {result['settings_key']}")
        return RedirectResponse(
            (
                f"/settings?flash={flash}&generated_key={generated_key}"
                f"&generated_key_expires_at=uso+interno+por+servidor"
            ),
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+criar+servidor+seguro:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/secure-connection-config/{settings_key}/rotate-key')
def settings_rotate_secure_connection_key(
    settings_key: str,
    access_key_field: str = Form('api_key'),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        result = control.rotate_secure_connection_key(
            settings_key=settings_key,
            access_key_field=access_key_field or None,
            actor=current_user.username,
        )
        generated_key = quote_plus(str(result['generated_access_key']))
        flash = quote_plus(f"Chave rotacionada para {settings_key}")
        return RedirectResponse(
            (
                f"/settings?flash={flash}&generated_key={generated_key}"
                f"&generated_key_expires_at=uso+interno+por+servidor"
            ),
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+rotacionar+chave+do+servidor:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/secure-connection-config/{settings_key}/update-secret')
def settings_update_secure_connection_secret(
    settings_key: str,
    secret_settings_json: str = Form('{}'),
    merge_mode: str = Form('true'),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    control = ControlService()
    try:
        secret_settings_payload = json.loads(secret_settings_json or '{}')
        if not isinstance(secret_settings_payload, dict):
            raise ValueError('Payload secreto deve ser um objeto JSON.')
        control.update_secure_connection_secret(
            settings_key=settings_key,
            secret_settings={str(key): str(value) for key, value in secret_settings_payload.items()},
            merge=merge_mode.lower() == 'true',
            actor=current_user.username,
        )
        flash = quote_plus(f"Segredo do servidor atualizado: {settings_key}")
        return RedirectResponse(
            f"/settings?flash={flash}",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+atualizar+segredo+do+servidor:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/dashboard/jobs/{job_id}/retry')
def dashboard_retry_job(
    request: Request,
    job_id: str,
    _: object = Depends(require_web_permission('jobs.retry')),
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
    empresa_id: str | None = Form(None),
    scope_type: str | None = Form(None),
    allowed_branch_codes: list[str] = Form([]),
    _: object = Depends(require_web_permission('users.manage')),
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))
    try:
        service.create_user_with_audit(
            UserCreateRequest(
                username=username,
                full_name=full_name,
                password=password,
                role=role,
                empresa_id=empresa_id,
                scope_type=scope_type,
                allowed_branch_codes=allowed_branch_codes,
            ),
            actor=request.session.get('username', 'system'),
            audit_context=build_request_audit_context(request),
        )
        return RedirectResponse('/settings?flash=Usuario+criado+com+sucesso', status_code=status.HTTP_302_FOUND)
    except (HTTPException, ValidationError) as exc:
        detail = quote_plus(str(getattr(exc, 'detail', exc)))
        return RedirectResponse(f'/settings?error={detail}', status_code=status.HTTP_302_FOUND)


@router.post('/settings/users/{user_id}')
def settings_update_user(
    request: Request,
    user_id: int,
    full_name: str = Form(...),
    role: str = Form('viewer'),
    empresa_id: str | None = Form(None),
    scope_type: str | None = Form(None),
    allowed_branch_codes: list[str] = Form([]),
    is_active: str = Form('true'),
    password: str = Form(''),
    _: object = Depends(require_web_permission('users.manage')),
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))
    try:
        service.update_user_with_audit(
            user_id,
            UserUpdateRequest(
                full_name=full_name,
                role=role,
                empresa_id=empresa_id,
                scope_type=scope_type,
                allowed_branch_codes=allowed_branch_codes,
                is_active=is_active.lower() == 'true',
                password=password or None,
            ),
            actor=request.session.get('username', 'system'),
            audit_context=build_request_audit_context(request),
        )
        return RedirectResponse('/settings?flash=Usuario+atualizado+com+sucesso', status_code=status.HTTP_302_FOUND)
    except (HTTPException, ValidationError) as exc:
        detail = quote_plus(str(getattr(exc, 'detail', exc)))
        return RedirectResponse(f'/settings?error={detail}', status_code=status.HTTP_302_FOUND)


@router.get('/dashboard/audit.csv')
def export_dashboard_audit_csv(
    _: object = Depends(require_web_permission('settings.manage')),
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


@router.get('/dashboard/audit.xlsx')
def export_dashboard_audit_xlsx(
    _: object = Depends(require_web_permission('settings.manage')),
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
    payload = audit_to_xlsx_bytes(rows)
    return Response(
        content=payload,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=audit_dashboard.xlsx'},
    )


@router.get('/dashboard/audit.pdf')
def export_dashboard_audit_pdf(
    _: object = Depends(require_web_permission('settings.manage')),
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
    payload = audit_to_pdf_bytes(rows)
    return Response(
        content=payload,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=audit_dashboard.pdf'},
    )


@router.get('/dashboard/export.md')
def export_dashboard_markdown(
    _: object = Depends(require_web_permission('settings.manage')),
    db: Session = Depends(get_db),
    company_code: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
):
    control = ControlService()
    sync_repo = SyncRepository(db)
    summary = sync_repo.dashboard_counts(
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    batches = sync_repo.latest_batches(
        limit=25,
        company_code=company_code,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    markdown_lines = [
        '# Snapshot local do sync-admin',
        '',
        f'- Gerado em: {summary["last_received"] or "-"}',
        f'- Total de lotes: {summary["total_batches"]}',
        f'- Total de registros: {summary["total_records"]}',
        f'- Falhas: {summary["failed_batches"]}',
        '',
        '## Ultimos lotes',
        '',
        '| id | empresa | filial | terminal | status | registros | recebido em |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in batches:
        markdown_lines.append(
            f'| {row.id} | {row.company_code} | {row.branch_code} | {row.terminal_code} | {row.status} | {row.records_received} | {row.received_at} |'
        )
    markdown_lines.extend(
        [
            '',
            audit_to_markdown(control.recent_agent_errors(limit=25), title='Erros recentes'),
        ]
    )
    markdown = '\n'.join(markdown_lines)
    vault_root = Path(__file__).resolve().parents[4] / '.cerebro-vivo' / 'Conhecimento' / 'hubs' / 'sync-admin'
    snapshot_path = write_markdown_snapshot(vault_root / 'snapshot.md', markdown)
    return Response(
        content=snapshot_path.read_text(encoding='utf-8'),
        media_type='text/markdown',
        headers={'Content-Disposition': 'attachment; filename=sync-admin-snapshot.md'},
    )
