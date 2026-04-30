from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import json
from math import ceil
from pathlib import Path
from urllib.parse import quote_plus, urlencode

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
from app.services.client_scope_service import ClientReportScope, ClientScopeService
from app.services.control_service import ControlService, SourceCycleSummary, SyncJobsSummary, TenantObservabilitySummary
from app.services.dashboard_service import DashboardService
from app.services.remote_agent_service import RemoteAgentService
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
from app.services.report_totalizer_service import build_report_pdf_summary
from app.services.user_service import UserService
from app.schemas.users import UserCreateRequest, UserUpdateRequest
from app.web.deps import ROLE_PERMISSIONS, require_client_portal_access, require_web_permission, require_web_user

router = APIRouter(tags=['web'])
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))
templates.env.globals['settings'] = settings
MAX_REPORT_WINDOW_DAYS = 427
REPORT_AUTO_REFRESH_SECONDS = 60

REPORT_VIEW_CONFIG = {
    'dashboard': {
        'label': 'Dashboard',
        'title': 'Dashboard de Relatorios',
        'description': 'Visao resumida com indicadores, graficos e atalhos para relatorios detalhados.',
    },
    'daily_revenue': {
        'label': 'Faturamento do Dia',
        'title': 'Faturamento do Dia',
        'description': 'Resumo consolidado do periodo com produtos, formas de pagamento e total geral.',
    },
    'payments': {
        'label': 'Formas de Pagamento',
        'title': 'Relatorio por Forma de Pagamento',
        'description': 'Participacao, quantidade de vendas e faturamento por meio de pagamento.',
    },
    'products': {
        'label': 'Produtos',
        'title': 'Relatorio por Produto',
        'description': 'Ranking, quantidade, valor medio e faturamento por codigo local de produto.',
    },
    'families': {
        'label': 'Familias',
        'title': 'Relatorio por Familia',
        'description': 'Totais agrupados por familia e categoria de produto.',
    },
    'terminals': {
        'label': 'Terminais',
        'title': 'Relatorio por Terminal',
        'description': 'Faturamento, quantidade e ticket medio por PDV.',
    },
    'sales': {
        'label': 'Vendas Detalhadas',
        'title': 'Vendas Detalhadas',
        'description': 'Tabela operacional com busca, ordenacao, paginacao e exportacao.',
    },
}

REPORT_ACTIONS = [
    ('daily_revenue', 'today', 'Faturamento do Dia', 'Total, produtos e pagamentos do dia.'),
    ('payments', 'custom', 'Por Pagamento', 'Dinheiro, Pix, cartoes e demais meios.'),
    ('products', 'custom', 'Por Produto', 'Ranking por codigo local e faturamento.'),
    ('families', 'custom', 'Por Familia', 'Agrupamento por familia e categoria.'),
    ('terminals', 'custom', 'Por Terminal', 'PDV, ticket medio e movimento.'),
    ('sales', 'custom', 'Vendas Detalhadas', 'Lista completa filtravel e exportavel.'),
]

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


def _resolve_report_period(period_preset: str | None, start_date: str | None, end_date: str | None) -> tuple[str | None, str | None, str]:
    if start_date or end_date:
        start = _parse_date(start_date)
        end = _parse_date(end_date) or date.today()
        if start is None:
            start = end - timedelta(days=MAX_REPORT_WINDOW_DAYS)
        if end < start:
            start, end = end, start
        min_start = end - timedelta(days=MAX_REPORT_WINDOW_DAYS)
        if start < min_start:
            start = min_start
        return start.isoformat(), end.isoformat(), period_preset or "custom"

    today = date.today()
    preset = period_preset or ""
    if preset == "today":
        return today.isoformat(), today.isoformat(), preset
    if preset == "month":
        return today.replace(day=1).isoformat(), today.isoformat(), preset
    if preset == "quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        return today.replace(month=quarter_month, day=1).isoformat(), today.isoformat(), preset
    if preset == "semester":
        semester_month = 1 if today.month <= 6 else 7
        return today.replace(month=semester_month, day=1).isoformat(), today.isoformat(), preset
    if preset == "year":
        return today.replace(month=1, day=1).isoformat(), today.isoformat(), preset
    return (today - timedelta(days=MAX_REPORT_WINDOW_DAYS)).isoformat(), today.isoformat(), "custom"


def _period_label(period_preset: str) -> str:
    return {
        "today": "Vendas do dia",
        "month": "Mensal",
        "quarter": "Trimestral",
        "semester": "Semestral",
        "year": "Anual",
        "custom": "Personalizado",
    }.get(period_preset, "Personalizado")


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


def _parse_timestamp(value: object) -> datetime | None:
    if value in (None, ''):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _format_signed(value: float, decimals: int = 2) -> str:
    return f'{value:+.{decimals}f}'


def _format_decimal(value: float, decimals: int = 2) -> str:
    return f'{value:.{decimals}f}'


_PAYMENT_NUMERIC_FIELDS = (
    'total_records',
    'quantity_sold',
    'gross_value',
    'discount_value',
    'surcharge_value',
    'total_sales_value',
)

_PAYMENT_MONEY_FIELDS = (
    'gross_value',
    'discount_value',
    'surcharge_value',
    'total_sales_value',
)


def _split_payment_label(label: object) -> list[str]:
    raw_label = str(label or '').strip()
    if not raw_label or raw_label == '-':
        return ['Nao informado']

    labels: list[str] = []
    seen: set[str] = set()
    for part in raw_label.split(','):
        normalized = ' '.join(str(part or '').split())
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        labels.append(normalized)
    return labels or ['Nao informado']


def _normalize_payment_breakdown_items(items: list[dict]) -> list[dict]:
    grouped: dict[str, dict[str, object]] = {}
    for item in items:
        labels = _split_payment_label(item.get('label'))
        allocation = 1 / len(labels)
        for label in labels:
            row = grouped.setdefault(
                label,
                {
                    'label': label,
                    'total_records': 0.0,
                    'quantity_sold': 0.0,
                    'gross_value': 0.0,
                    'discount_value': 0.0,
                    'surcharge_value': 0.0,
                    'total_sales_value': 0.0,
                },
            )
            for field in _PAYMENT_NUMERIC_FIELDS:
                row[field] = _safe_float(row.get(field)) + (_safe_float(item.get(field)) * allocation)

    normalized_items = list(grouped.values())
    normalized_items.sort(key=lambda row: _safe_float(row.get('total_sales_value')), reverse=True)
    for row in normalized_items:
        row['total_records'] = str(int(round(_safe_float(row.get('total_records')))))
        row['quantity_sold'] = _format_decimal(_safe_float(row.get('quantity_sold')), decimals=3)
        for field in _PAYMENT_MONEY_FIELDS:
            row[field] = _format_decimal(_safe_float(row.get(field)))
    return normalized_items


def _source_status_snapshot(source_configs: list[dict], sync_jobs: list[dict]) -> dict[str, dict[str, str]]:
    latest_by_source: dict[str, dict[str, str]] = {}
    counts_by_source: dict[str, dict[str, int]] = {}
    ordered_jobs = sorted(
        sync_jobs,
        key=lambda item: str(
            item.get('updated_at')
            or item.get('finished_at')
            or item.get('started_at')
            or item.get('scheduled_at')
            or item.get('created_at')
            or ''
        ),
        reverse=True,
    )

    for job in sync_jobs:
        source_config_id = str(job.get('source_config_id') or '')
        if not source_config_id:
            continue
        status = str(job.get('status') or 'pending').lower()
        counters = counts_by_source.setdefault(
            source_config_id,
            {'queued_count': 0, 'running_count': 0, 'done_count': 0, 'failed_count': 0},
        )
        if status in {'pending', 'queued'}:
            counters['queued_count'] += 1
        elif status in {'processing', 'running'}:
            counters['running_count'] += 1
        elif status == 'done':
            counters['done_count'] += 1
        elif status in {'failed', 'dead_letter'}:
            counters['failed_count'] += 1

    for job in ordered_jobs:
        source_config_id = str(job.get('source_config_id') or '')
        if not source_config_id or source_config_id in latest_by_source:
            continue
        status = str(job.get('status') or 'pending').lower()
        if status == 'processing':
            live_status = 'running'
        elif status == 'pending':
            live_status = 'queued'
        elif status == 'done':
            live_status = 'done'
        elif status in {'failed', 'dead_letter'}:
            live_status = 'failed'
        else:
            live_status = status
        last_action_at = (
            job.get('finished_at')
            or job.get('started_at')
            or job.get('scheduled_at')
            or job.get('created_at')
            or '-'
        )
        latest_by_source[source_config_id] = {
            'live_status': live_status,
            'last_action': status,
            'last_action_at': str(last_action_at),
            'job_id': str(job.get('id') or '-'),
        }

    for source in source_configs:
        source_id = str(source.get('id') or '')
        if not source_id or source_id in latest_by_source:
            continue
        fallback_action_at = source.get('last_run_at') or source.get('last_scheduled_at') or '-'
        latest_by_source[source_id] = {
            'live_status': str(source.get('last_status') or 'pending'),
            'last_action': str(source.get('last_status') or 'pending'),
            'last_action_at': str(fallback_action_at),
            'job_id': '-',
        }

    for source_id, counters in counts_by_source.items():
        snapshot = latest_by_source.setdefault(
            source_id,
            {
                'live_status': 'pending',
                'last_action': 'pending',
                'last_action_at': '-',
                'job_id': '-',
            },
        )
        snapshot.update({key: str(value) for key, value in counters.items()})

    for source in source_configs:
        source_id = str(source.get('id') or '')
        if not source_id:
            continue
        snapshot = latest_by_source.setdefault(
            source_id,
            {
                'live_status': str(source.get('last_status') or 'pending'),
                'last_action': str(source.get('last_status') or 'pending'),
                'last_action_at': str(source.get('last_run_at') or source.get('last_scheduled_at') or '-'),
                'job_id': '-',
            },
        )
        snapshot.setdefault('queued_count', '0')
        snapshot.setdefault('running_count', '0')
        snapshot.setdefault('done_count', '0')
        snapshot.setdefault('failed_count', '0')

    return latest_by_source


def _source_execution_overview(source_status_snapshot: dict[str, dict[str, str]]) -> dict[str, int]:
    overview = {
        'queued_count': 0,
        'running_count': 0,
        'done_count': 0,
        'failed_count': 0,
    }
    for snapshot in source_status_snapshot.values():
        for key in overview:
            try:
                overview[key] += int(snapshot.get(key, 0) or 0)
            except (TypeError, ValueError):
                continue
    return overview


def _source_attention_rows(
    source_configs: list[dict],
    source_status_snapshot: dict[str, dict[str, str]],
) -> list[dict[str, object]]:
    now = datetime.now(UTC)
    rows: list[dict[str, object]] = []

    for source in source_configs:
        source_id = str(source.get('id') or '')
        if not source_id:
            continue

        snapshot = source_status_snapshot.get(source_id, {})
        live_status = str(source.get('last_status') or snapshot.get('live_status') or 'pending').lower()
        queued_count = int(snapshot.get('queued_count', 0) or 0)
        running_count = int(snapshot.get('running_count', 0) or 0)
        failed_count = int(snapshot.get('failed_count', 0) or 0)
        next_run_at = _parse_timestamp(source.get('next_run_at'))
        last_run_at = _parse_timestamp(source.get('last_run_at'))
        last_error = str(source.get('last_error') or '').strip()

        reasons: list[str] = []
        severity = 0

        if failed_count > 0 or live_status in {'failed', 'dead_letter', 'retrying'} or last_error:
            severity += 3
            reasons.append('falha recente')
        if next_run_at is not None and next_run_at <= now:
            severity += 2
            reasons.append('agendada em atraso')
        if live_status in {'queued', 'running'} or queued_count > 0 or running_count > 0:
            severity += 1
            if live_status == 'running' or running_count > 0:
                reasons.append('em execucao')
            else:
                reasons.append('na fila')

        if severity == 0:
            continue

        rows.append(
            {
                'id': source_id,
                'nome': str(source.get('nome') or source_id),
                'connector_type': str(source.get('connector_type') or '-'),
                'status': live_status,
                'status_label': str(source.get('last_status') or live_status),
                'reason': '; '.join(dict.fromkeys(reasons)) or 'atencao operacional',
                'next_run_at': str(source.get('next_run_at') or '-'),
                'last_action_at': str(
                    snapshot.get('last_action_at')
                    or source.get('last_run_at')
                    or source.get('last_scheduled_at')
                    or '-'
                ),
                'last_error': last_error or '-',
                'queued_count': queued_count,
                'running_count': running_count,
                'failed_count': failed_count,
                'sort_severity': severity,
                'sort_next_run_at': (
                    next_run_at.isoformat() if next_run_at is not None else datetime.max.replace(tzinfo=UTC).isoformat()
                ),
                'sort_last_run_at': (
                    last_run_at.isoformat() if last_run_at is not None else datetime.max.replace(tzinfo=UTC).isoformat()
                ),
            }
        )

    rows.sort(
        key=lambda item: (
            -int(item['sort_severity']),
            item['sort_next_run_at'],
            item['sort_last_run_at'],
            str(item['nome']).lower(),
        )
    )
    return rows[:5]


def _source_attention_summary(source_attention_rows: list[dict[str, object]]) -> dict[str, int]:
    summary = {
        'total_count': len(source_attention_rows),
        'failed_count': 0,
        'queued_count': 0,
        'running_count': 0,
        'overdue_count': 0,
    }
    now = datetime.now(UTC)
    for row in source_attention_rows:
        status = str(row.get('status') or '').lower()
        reason = str(row.get('reason') or '').lower()
        if status == 'failed' or 'falha' in reason:
            summary['failed_count'] += 1
        elif status == 'running' or 'execucao' in reason:
            summary['running_count'] += 1
        elif status == 'queued' or 'fila' in reason:
            summary['queued_count'] += 1
        next_run_at = _parse_timestamp(row.get('next_run_at'))
        if next_run_at is not None and next_run_at <= now:
            summary['overdue_count'] += 1
    return summary


def _current_month_range() -> tuple[str, str]:
    today = date.today()
    start = today.replace(day=1)
    return start.isoformat(), today.isoformat()


def _commercial_snapshot(overview: dict, top_products: dict) -> dict[str, object]:
    top_items = list(top_products.get('items', [])) if isinstance(top_products, dict) else []
    top_item = top_items[0] if top_items else {}
    return {
        'period_start': overview.get('start_date') or '-',
        'period_end': overview.get('end_date') or '-',
        'total_records': int(overview.get('total_records', 0) or 0),
        'total_sales_value': _format_decimal(_safe_float(overview.get('total_sales_value'))),
        'distinct_products': int(overview.get('distinct_products', 0) or 0),
        'average_ticket': _format_decimal(
            (_safe_float(overview.get('total_sales_value')) / int(overview.get('total_records', 0) or 0))
            if int(overview.get('total_records', 0) or 0)
            else 0.0
        ),
        'top_product': str(top_item.get('produto') or '-'),
        'top_product_value': _format_decimal(_safe_float(top_item.get('total_sales_value'))),
    }


def _remote_client_fleet_overview(fleet_summary) -> dict[str, int]:
    total_clients = int(getattr(fleet_summary, 'total_clients', 0) or 0)
    online_clients = int(getattr(fleet_summary, 'online_clients', 0) or 0)
    error_clients = int(getattr(fleet_summary, 'error_clients', 0) or 0)
    offline_clients = max(0, total_clients - online_clients - error_clients)
    return {
        'total_clients': total_clients,
        'online_clients': online_clients,
        'error_clients': error_clients,
        'offline_clients': offline_clients,
    }


def _remote_client_health_snapshot(client_data: dict) -> dict[str, object]:
    now = datetime.now(UTC)
    config_snapshot = client_data.get('config_snapshot') if isinstance(client_data.get('config_snapshot'), dict) else {}
    try:
        sync_interval_minutes = int(config_snapshot.get('sync_interval_minutes') or 0)
    except (TypeError, ValueError):
        sync_interval_minutes = 0
    grace_minutes = max(30, sync_interval_minutes * 2 if sync_interval_minutes else 30)

    last_sync_at = _parse_timestamp(client_data.get('last_sync_at'))
    last_poll_at = _parse_timestamp(client_data.get('last_command_poll_at'))
    sync_lag_minutes = None
    poll_lag_minutes = None
    if last_sync_at is not None:
        sync_lag_minutes = max(0.0, (now - last_sync_at).total_seconds() / 60.0)
    if last_poll_at is not None:
        poll_lag_minutes = max(0.0, (now - last_poll_at).total_seconds() / 60.0)

    status = str(client_data.get('status') or 'unknown').lower()
    stale_sync = sync_lag_minutes is None or sync_lag_minutes > grace_minutes
    stale_poll = poll_lag_minutes is None or poll_lag_minutes > grace_minutes

    if status in {'error', 'failed', 'offline'} or (stale_sync and stale_poll):
        level = 'error'
        label = 'error'
        reason = 'Sync e poll fora da janela esperada'
    elif stale_sync or stale_poll:
        level = 'warning'
        label = 'warning'
        reason = 'Sync ou poll fora da janela esperada'
    else:
        level = 'online'
        label = 'online'
        reason = 'Sync e poll recentes'

    return {
        'level': level,
        'label': label,
        'reason': reason,
        'grace_minutes': grace_minutes,
        'sync_lag_minutes': None if sync_lag_minutes is None else round(sync_lag_minutes, 1),
        'poll_lag_minutes': None if poll_lag_minutes is None else round(poll_lag_minutes, 1),
    }


def _remote_agent_operational_snapshot(remote_agent_snapshot: dict[str, object]) -> dict[str, object]:
    now = datetime.now(UTC)
    last_registration_at = _parse_timestamp(remote_agent_snapshot.get('last_registration_at'))
    last_command_poll_at = _parse_timestamp(remote_agent_snapshot.get('last_command_poll_at'))
    pull_enabled = bool(settings.remote_command_pull_enabled)
    grace_minutes = max(30, int(settings.remote_command_pull_interval_seconds / 60) * 2 or 30)

    registration_lag_minutes = None
    poll_lag_minutes = None
    if last_registration_at is not None:
        registration_lag_minutes = max(0.0, (now - last_registration_at).total_seconds() / 60.0)
    if last_command_poll_at is not None:
        poll_lag_minutes = max(0.0, (now - last_command_poll_at).total_seconds() / 60.0)

    stale_registration = registration_lag_minutes is None or registration_lag_minutes > grace_minutes
    stale_poll = poll_lag_minutes is None or poll_lag_minutes > grace_minutes

    if not pull_enabled:
        level = 'disabled'
        label = 'disabled'
        reason = 'Pull remoto desabilitado'
    elif stale_registration and stale_poll:
        level = 'error'
        label = 'error'
        reason = 'Registro e poll remoto fora da janela'
    elif stale_registration or stale_poll:
        level = 'warning'
        label = 'warning'
        reason = 'Registro ou poll remoto fora da janela'
    else:
        level = 'online'
        label = 'online'
        reason = 'Registro e poll remoto recentes'

    return {
        'level': level,
        'label': label,
        'reason': reason,
        'grace_minutes': grace_minutes,
        'registration_lag_minutes': None if registration_lag_minutes is None else round(registration_lag_minutes, 1),
        'poll_lag_minutes': None if poll_lag_minutes is None else round(poll_lag_minutes, 1),
        'pull_enabled': pull_enabled,
    }


def _build_filter_chips(
    *,
    period_preset: str,
    start_date: str | None,
    end_date: str | None,
    start_time: str | None,
    end_time: str | None,
    branch_code: str | None,
    terminal_code: str | None,
    category: str | None,
    product: str | None = None,
    product_code: str | None = None,
    family: str | None = None,
    payment_method: str | None = None,
    card_brand: str | None = None,
    operator: str | None = None,
    customer: str | None = None,
    canceled: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
) -> list[dict[str, str]]:
    period_value = 'Todo o periodo'
    if start_date and end_date:
        period_value = f'{start_date} ate {end_date}'
    elif start_date:
        period_value = f'A partir de {start_date}'
    elif end_date:
        period_value = f'Ate {end_date}'

    return [
        {'label': 'Atalho', 'value': _period_label(period_preset)},
        {'label': 'Periodo', 'value': period_value},
        {'label': 'Horario', 'value': f'{start_time or "00:00"} ate {end_time or "23:59"}'},
        {'label': 'Filial', 'value': branch_code or 'Todas'},
        {'label': 'Terminal', 'value': terminal_code or 'Todos'},
        {'label': 'Categoria', 'value': category or 'Todas'},
        {'label': 'Produto', 'value': product or product_code or 'Todos'},
        {'label': 'Familia', 'value': family or 'Todas'},
        {'label': 'Pagamento', 'value': payment_method or 'Todos'},
        {'label': 'Bandeira', 'value': card_brand or 'Todas'},
        {'label': 'Operador', 'value': operator or 'Todos'},
        {'label': 'Cliente', 'value': customer or 'Todos'},
        {'label': 'Cancelada', 'value': canceled or 'Todas'},
        {'label': 'Status', 'value': status_filter or 'Todos'},
        {'label': 'Tipo', 'value': report_type or 'Vendas'},
        {'label': 'Top produtos', 'value': str(top_limit)},
        {'label': 'Vendas recentes', 'value': str(recent_limit)},
    ]


def _normalize_report_view(report_view: str | None) -> str:
    if report_view in REPORT_VIEW_CONFIG:
        return str(report_view)
    return 'dashboard'


def _build_report_link(request: Request, **overrides: str | int | None) -> str:
    params = dict(request.query_params)
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = str(value)
    return f'{request.url.path}?{urlencode(params)}'


def _build_report_actions(request: Request, *, selected_empresa_id: str | None) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for view, preset, label, description in REPORT_ACTIONS:
        overrides: dict[str, str | int | None] = {
            'report_view': view,
            'period_preset': preset,
        }
        if selected_empresa_id:
            overrides['empresa_id'] = selected_empresa_id
        if view == 'daily_revenue':
            overrides['top_limit'] = 10
            overrides['recent_limit'] = 20
        actions.append(
            {
                'view': view,
                'label': label,
                'description': description,
                'href': _build_report_link(request, **overrides),
            }
        )
    return actions


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


def _build_sync_status(empresa_id: str | None) -> dict[str, object]:
    control = ControlService()
    clients = control.fetch_remote_clients(empresa_id=empresa_id)
    if not clients:
        return {
            'status': 'offline',
            'label': 'Sem agente',
            'last_sync_at': 'Sem agente',
            'sync_lag_minutes': None,
            'reason': 'Nenhuma API local conectada para o tenant filtrado.',
        }
    snapshots = [_remote_client_health_snapshot(client) for client in clients]
    level_order = {'error': 3, 'warning': 2, 'offline': 3, 'online': 1, 'unknown': 0}
    worst = max(snapshots, key=lambda item: level_order.get(str(item.get('level')), 0))
    latest_client = max(
        clients,
        key=lambda item: _parse_timestamp(item.get('last_sync_at')) or datetime.min.replace(tzinfo=UTC),
    )
    latest_sync = _parse_timestamp(latest_client.get('last_sync_at'))
    return {
        'status': worst.get('level') or 'unknown',
        'label': worst.get('label') or 'unknown',
        'last_sync_at': latest_sync.isoformat(timespec='minutes') if latest_sync else 'Sem sync',
        'sync_lag_minutes': worst.get('sync_lag_minutes'),
        'reason': worst.get('reason') or 'Status operacional calculado pela frota conectada.',
    }


def _build_kpi_cards(
    *,
    overview: dict,
    comparison: dict | None,
    sync_status: dict[str, object],
) -> list[dict[str, str]]:
    total_records = int(overview.get('total_records', 0) or 0)
    total_sales = _safe_float(overview.get('total_sales_value'))
    distinct_products = int(overview.get('distinct_products', 0) or 0)
    average_ticket = total_sales / total_records if total_records else 0.0
    previous_total = _safe_float((comparison or {}).get('previous_total_sales_value'))
    growth_pct = comparison.get('delta_total_sales_value_pct') if comparison else None
    if comparison is None:
        growth_value = 'Sem base'
        growth_hint = 'Filtro sem periodo anterior valido para comparacao.'
        growth_tone = 'neutral'
    elif growth_pct is None and total_sales > 0 and previous_total == 0:
        growth_value = 'Novo'
        growth_hint = 'Periodo anterior sem faturamento para comparar.'
        growth_tone = 'success'
    elif growth_pct is None:
        growth_value = '0.0%'
        growth_hint = 'Sem variacao calculavel no periodo anterior.'
        growth_tone = 'neutral'
    else:
        growth_value = f'{growth_pct}%'
        growth_hint = 'Comparado ao periodo anterior.'
        growth_tone = 'success'
    if growth_value.startswith('-'):
        growth_tone = 'error'
    elif growth_value in {'0.0%', '+0.0%', 'Sem base'}:
        growth_tone = 'neutral'
    return [
        {
            'key': 'total_sales',
            'icon': 'R$',
            'label': 'Faturamento total',
            'value': _format_decimal(total_sales),
            'hint': 'Receita liquida do periodo filtrado.',
            'tone': 'success',
        },
        {
            'key': 'total_records',
            'icon': 'NV',
            'label': 'Total de vendas',
            'value': str(total_records),
            'hint': 'Registros comerciais sincronizados.',
            'tone': 'primary',
        },
        {
            'key': 'average_ticket',
            'icon': 'TM',
            'label': 'Ticket medio',
            'value': _format_decimal(average_ticket),
            'hint': 'Media de faturamento por venda.',
            'tone': 'info',
        },
        {
            'key': 'growth',
            'icon': 'TR',
            'label': 'Crescimento',
            'value': growth_value,
            'hint': growth_hint,
            'tone': growth_tone,
        },
        {
            'key': 'items',
            'icon': 'SKU',
            'label': 'Quantidade de itens',
            'value': str(distinct_products),
            'hint': 'Produtos distintos vendidos.',
            'tone': 'warning',
        },
        {
            'key': 'last_sync',
            'icon': 'SYNC',
            'label': 'Status da sincronizacao',
            'value': str(sync_status.get('last_sync_at') or sync_status.get('label') or 'Sem sync'),
            'hint': str(sync_status.get('reason') or '-'),
            'tone': str(sync_status.get('status') or 'neutral'),
        },
    ]


def _report_api_params(
    *,
    request: Request,
    base_path: str,
    empresa_id: str | None,
) -> dict[str, str]:
    params = dict(request.query_params)
    if empresa_id:
        params['empresa_id'] = empresa_id
    query = '&'.join(f'{key}={value}' for key, value in params.items() if value not in (None, ''))
    return {
        'dashboard': f'{base_path}/dashboard?{query}' if query else f'{base_path}/dashboard',
        'kpis': f'{base_path}/kpis?{query}' if query else f'{base_path}/kpis',
        'charts': f'{base_path}/charts?{query}' if query else f'{base_path}/charts',
        'table': f'{base_path}/table?{query}' if query else f'{base_path}/table',
        'sync_status': f'{base_path}/sync-status?{query}' if query else f'{base_path}/sync-status',
    }


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
    period_preset: str | None = None,
    start_date: str | None,
    end_date: str | None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None,
    terminal_code: str | None,
    top_limit: int,
    recent_limit: int,
    category: str | None = None,
    product: str | None = None,
    product_code: str | None = None,
    family: str | None = None,
    payment_method: str | None = None,
    card_brand: str | None = None,
    canceled: str | None = None,
    operator: str | None = None,
    customer: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    report_view: str | None = None,
) -> dict:
    control = ControlService()
    normalized_top_limit = max(1, min(top_limit, 20))
    normalized_recent_limit = max(1, min(recent_limit, 50))
    start_date, end_date, normalized_period_preset = _resolve_report_period(period_preset, start_date, end_date)
    overview = control.fetch_report_overview(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
    )
    daily_sales = control.fetch_report_daily_sales(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
    )
    top_products = control.fetch_report_top_products(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=normalized_top_limit,
    )
    sales_by_type = control.fetch_report_breakdown(
        empresa_id=empresa_id,
        group_by='tipo_venda',
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=normalized_top_limit,
    )
    sales_by_payment = control.fetch_report_breakdown(
        empresa_id=empresa_id,
        group_by='forma_pagamento',
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=100,
    )
    sales_by_family = control.fetch_report_breakdown(
        empresa_id=empresa_id,
        group_by='familia_produto',
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=normalized_top_limit,
    )
    sales_by_terminal = control.fetch_report_breakdown(
        empresa_id=empresa_id,
        group_by='terminal_code',
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=normalized_top_limit,
    )
    recent_sales = control.fetch_report_recent_sales(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        status_filter=status_filter,
        canceled=canceled,
        operator=operator,
        customer=customer,
        start_time=start_time,
        end_time=end_time,
        limit=normalized_recent_limit,
    )
    daily_items = list(daily_sales.get('items', []))
    top_items = list(top_products.get('items', []))
    type_items = list(sales_by_type.get('items', []))
    payment_items = _normalize_payment_breakdown_items(list(sales_by_payment.get('items', [])))
    family_items = list(sales_by_family.get('items', []))
    terminal_items = list(sales_by_terminal.get('items', []))
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
            category=category,
            product=product,
            product_code=product_code,
            family=family,
            payment_method=payment_method,
            card_brand=card_brand,
            status_filter=status_filter,
            canceled=canceled,
            operator=operator,
            customer=customer,
            start_time=start_time,
            end_time=end_time,
        )
    comparison = _build_comparison(
        current_overview=overview,
        previous_overview=previous_overview,
        previous_period=previous_period,
    )
    sync_status = _build_sync_status(empresa_id)
    kpi_cards = _build_kpi_cards(
        overview=overview,
        comparison=comparison,
        sync_status=sync_status,
    )
    highlight_cards = _build_report_highlights(
        overview=overview,
        daily_items=daily_items,
        top_items=top_items,
    )
    filter_chips = _build_filter_chips(
        period_preset=normalized_period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        operator=operator,
        customer=customer,
        canceled=canceled,
        status_filter=status_filter,
        report_type=report_type,
        top_limit=normalized_top_limit,
        recent_limit=normalized_recent_limit,
    )
    normalized_report_view = _normalize_report_view(report_view)
    return {
        'overview': overview,
        'daily_items': daily_items,
        'top_items': top_items,
        'type_items': type_items,
        'payment_items': payment_items,
        'family_items': family_items,
        'terminal_items': terminal_items,
        'recent_items': recent_items,
        'comparison': comparison,
        'sync_status': sync_status,
        'kpi_cards': kpi_cards,
        'highlight_cards': highlight_cards,
        'filter_chips': filter_chips,
        'period_preset': normalized_period_preset,
        'start_date': start_date or '',
        'end_date': end_date or '',
        'start_time': start_time or '',
        'end_time': end_time or '',
        'branch_code': branch_code or '',
        'terminal_code': terminal_code or '',
        'category': category or '',
        'product': product or '',
        'product_code': product_code or '',
        'family': family or '',
        'payment_method': payment_method or '',
        'card_brand': card_brand or '',
        'canceled': canceled or '',
        'operator': operator or '',
        'customer': customer or '',
        'status_filter': status_filter or '',
        'report_type': report_type or 'sales',
        'report_view': normalized_report_view,
        'report_view_config': REPORT_VIEW_CONFIG[normalized_report_view],
        'top_limit': normalized_top_limit,
        'recent_limit': normalized_recent_limit,
        'report_auto_refresh_seconds': REPORT_AUTO_REFRESH_SECONDS,
        'daily_chart_labels': json.dumps([item.get('day', '-') for item in daily_items]),
        'daily_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in daily_items]
        ),
        'top_chart_labels': json.dumps([item.get('produto', '-') for item in top_items]),
        'top_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in top_items]
        ),
        'type_chart_labels': json.dumps([item.get('label', '-') for item in type_items]),
        'type_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in type_items]
        ),
        'payment_chart_labels': json.dumps([item.get('label', '-') for item in payment_items]),
        'payment_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in payment_items]
        ),
        'family_chart_labels': json.dumps([item.get('label', '-') for item in family_items]),
        'family_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in family_items]
        ),
        'terminal_chart_labels': json.dumps([item.get('label', '-') for item in terminal_items]),
        'terminal_chart_values': json.dumps(
            [float(item.get('total_sales_value', 0) or 0) for item in terminal_items]
        ),
    }


def _advanced_report_params(request: Request) -> dict[str, str]:
    keys = (
        'product',
        'product_code',
        'family',
        'payment_method',
        'card_brand',
        'canceled',
        'operator',
        'customer',
    )
    return {key: request.query_params.get(key, '') for key in keys}


@router.get('/', response_class=HTMLResponse)
def root(request: Request):
    if request.session.get('user_id'):
        if request.session.get('user_role') == 'client':
            return RedirectResponse('/client/reports', status_code=status.HTTP_302_FOUND)
        return RedirectResponse('/dashboard', status_code=status.HTTP_302_FOUND)
    return RedirectResponse('/login', status_code=status.HTTP_302_FOUND)


@router.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, 'login.html', {'request': request, 'error': None})


@router.get('/client/login', response_class=HTMLResponse)
def client_login_page(request: Request):
    return templates.TemplateResponse(request, 'client_login.html', {'request': request, 'error': None})


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
        return RedirectResponse('/client/reports', status_code=status.HTTP_302_FOUND)
    return RedirectResponse('/dashboard', status_code=status.HTTP_302_FOUND)


@router.post('/client/login', response_class=HTMLResponse)
def client_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    svc = AuthService(db)
    user = svc.login(username, password)
    if not user or user.role not in {'client', 'admin'}:
        request.session.clear()
        return templates.TemplateResponse(
            request,
            'client_login.html',
            {'request': request, 'error': 'Credenciais invalidas para o portal do cliente'},
            status_code=400,
        )

    request.session['user_id'] = user.id
    request.session['username'] = user.username
    request.session['user_role'] = user.role
    request.session['empresa_id'] = user.empresa_id
    return RedirectResponse('/client/reports', status_code=status.HTTP_302_FOUND)


@router.post('/logout')
def logout(request: Request):
    user_role = request.session.get('user_role')
    request.session.clear()
    if user_role == 'client':
        return RedirectResponse('/client/login', status_code=status.HTTP_302_FOUND)
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
    current_period_start, current_period_end = _current_month_range()
    report_empresa_id = company_code or getattr(current_user, 'empresa_id', None) or settings.control_empresa_id
    try:
        commercial_payload = _build_report_payload(
            empresa_id=report_empresa_id,
            start_date=current_period_start,
            end_date=current_period_end,
            branch_code=branch_code,
            terminal_code=terminal_code,
            top_limit=3,
            recent_limit=5,
        )
    except Exception:
        commercial_payload = {
            'overview': {
                'start_date': current_period_start,
                'end_date': current_period_end,
                'total_records': 0,
                'total_sales_value': 0.0,
                'distinct_products': 0,
            },
            'daily_items': [],
            'top_items': [],
            'recent_items': [],
            'comparison': None,
            'highlight_cards': [],
            'filter_chips': [],
        }
    commercial_snapshot = _commercial_snapshot(
        commercial_payload['overview'],
        {'items': commercial_payload.get('top_items', [])},
    )
    try:
        remote_agent_snapshot = RemoteAgentService(db).build_status_snapshot()
    except Exception:
        remote_agent_snapshot = {
            'service': 'sync-admin',
            'hostname': '-',
            'last_sync_at': None,
            'last_sync_status': '-',
            'last_sync_reason': '-',
            'last_registration_at': None,
            'last_command_poll_at': None,
            'last_command_origin': '-',
            'pending_local_batches': 0,
            'total_local_records': 0,
        }
    remote_agent_operational = _remote_agent_operational_snapshot(remote_agent_snapshot)
    control_online = control_summary.api_health == 'online'
    if control_online:
        job_summary = control.fetch_sync_jobs_summary()
        tenant_observability = control.fetch_tenant_observability()
        source_configs = control.fetch_source_configs()
        sync_jobs = control.fetch_sync_jobs(limit=50)
        source_status_snapshot = _source_status_snapshot(source_configs, sync_jobs)
        source_execution_overview = _source_execution_overview(source_status_snapshot)
        source_cycle_summary = control.fetch_source_cycle_summary(source_configs)
        source_attention_rows = _source_attention_rows(source_configs, source_status_snapshot)
        source_attention_summary = _source_attention_summary(source_attention_rows)
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
        sync_jobs = []
        source_status_snapshot = {}
        source_execution_overview = {
            'queued_count': 0,
            'running_count': 0,
            'done_count': 0,
            'failed_count': 0,
        }
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
        source_attention_rows = []
        source_attention_summary = {
            'total_count': 0,
            'failed_count': 0,
            'queued_count': 0,
            'running_count': 0,
            'overdue_count': 0,
        }
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
            'sync_jobs': sync_jobs,
            'source_status_snapshot': source_status_snapshot,
            'source_execution_overview': source_execution_overview,
            'source_cycle_summary': source_cycle_summary,
            'source_attention_rows': source_attention_rows,
            'source_attention_summary': source_attention_summary,
            'commercial_snapshot': commercial_snapshot,
            'commercial_comparison': commercial_payload.get('comparison'),
            'commercial_highlight_cards': commercial_payload.get('highlight_cards', []),
            'remote_agent_snapshot': remote_agent_snapshot,
            'remote_agent_operational': remote_agent_operational,
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
    current_period_start, current_period_end = _current_month_range()
    report_empresa_id = company_code or settings.control_empresa_id
    try:
        commercial_payload = _build_report_payload(
            empresa_id=report_empresa_id,
            start_date=current_period_start,
            end_date=current_period_end,
            branch_code=branch_code,
            terminal_code=terminal_code,
            top_limit=3,
            recent_limit=5,
        )
    except Exception:
        commercial_payload = {
            'overview': {
                'start_date': current_period_start,
                'end_date': current_period_end,
                'total_records': 0,
                'total_sales_value': 0.0,
                'distinct_products': 0,
            },
            'daily_items': [],
            'top_items': [],
            'recent_items': [],
            'comparison': None,
            'highlight_cards': [],
            'filter_chips': [],
        }
    commercial_snapshot = _commercial_snapshot(
        commercial_payload['overview'],
        {'items': commercial_payload.get('top_items', [])},
    )
    try:
        remote_agent_snapshot = RemoteAgentService(db).build_status_snapshot()
    except Exception:
        remote_agent_snapshot = {
            'service': 'sync-admin',
            'hostname': '-',
            'last_sync_at': None,
            'last_sync_status': '-',
            'last_sync_reason': '-',
            'last_registration_at': None,
            'last_command_poll_at': None,
            'last_command_origin': '-',
            'pending_local_batches': 0,
            'total_local_records': 0,
        }
    remote_agent_operational = _remote_agent_operational_snapshot(remote_agent_snapshot)
    control_online = control_summary.api_health == 'online'
    if control_online:
        job_summary = control_service.fetch_sync_jobs_summary()
        tenant_observability = control_service.fetch_tenant_observability()
        source_configs = control_service.fetch_source_configs()
        sync_jobs = control_service.fetch_sync_jobs(limit=50)
        source_status_snapshot = _source_status_snapshot(source_configs, sync_jobs)
        source_execution_overview = _source_execution_overview(source_status_snapshot)
        source_cycle_summary = control_service.fetch_source_cycle_summary(source_configs)
        source_attention_rows = _source_attention_rows(source_configs, source_status_snapshot)
        source_attention_summary = _source_attention_summary(source_attention_rows)
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
        sync_jobs = []
        source_status_snapshot = {}
        source_execution_overview = {
            'queued_count': 0,
            'running_count': 0,
            'done_count': 0,
            'failed_count': 0,
        }
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
        source_attention_rows = []
        source_attention_summary = {
            'total_count': 0,
            'failed_count': 0,
            'queued_count': 0,
            'running_count': 0,
            'overdue_count': 0,
        }
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
            'sync_jobs': sync_jobs,
            'source_status_snapshot': source_status_snapshot,
            'source_execution_overview': source_execution_overview,
            'source_attention_rows': source_attention_rows,
            'source_attention_summary': source_attention_summary,
            'commercial_snapshot': commercial_snapshot,
            'commercial_comparison': commercial_payload.get('comparison'),
            'commercial_highlight_cards': commercial_payload.get('highlight_cards', []),
            'remote_agent': remote_agent_snapshot,
            'remote_agent_operational': remote_agent_operational,
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
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    report_view: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
    current_user: User = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        status_filter=status_filter,
        report_type=report_type,
        report_view=report_view,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    selected_empresa_id = empresa_id or settings.control_empresa_id
    return templates.TemplateResponse(
        request,
        'reports.html',
        {
            'request': request,
            'current_user': current_user,
            'selected_empresa_id': selected_empresa_id,
            'api_endpoints': _report_api_params(
                request=request,
                base_path='/reports/api',
                empresa_id=selected_empresa_id,
            ),
            'report_actions': _build_report_actions(
                request,
                selected_empresa_id=selected_empresa_id,
            ),
            **payload,
        },
    )


def _resolve_client_portal_scope(
    *,
    current_user: User,
    db: Session,
    requested_empresa_id: str | None,
    requested_branch_code: str | None,
    start_date: str | None,
    end_date: str | None,
    terminal_code: str | None,
) -> ClientReportScope:
    control = ControlService()
    if current_user.role == 'admin':
        empresa_id = requested_empresa_id or settings.control_empresa_id
        if not empresa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Informe empresa_id para visualizar o portal do cliente como admin.',
            )
        allowed_branch_codes = control.fetch_report_branch_options(
            empresa_id=empresa_id,
            start_date=start_date,
            end_date=end_date,
            terminal_code=terminal_code,
        )
        return ClientReportScope(
            empresa_id=empresa_id,
            allowed_branch_codes=allowed_branch_codes,
            selected_branch_code=requested_branch_code or None,
        )

    return ClientScopeService(
        control,
        UserBranchPermissionRepository(db),
    ).resolve(
        user=current_user,
        requested_branch_code=requested_branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )


@router.get('/client/dashboard', response_class=HTMLResponse)
def client_dashboard_page(
    request: Request,
    empresa_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    current_user: User = Depends(require_client_portal_access),
    db: Session = Depends(get_db),
):
    query = f'?{request.url.query}' if request.url.query else ''
    return RedirectResponse(f'/client/reports{query}', status_code=status.HTTP_302_FOUND)


@router.get('/client/reports', response_class=HTMLResponse)
def client_reports_page(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    report_view: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
    current_user: User = Depends(require_client_portal_access),
    db: Session = Depends(get_db),
):
    scope = _resolve_client_portal_scope(
        current_user=current_user,
        db=db,
        requested_empresa_id=empresa_id,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        status_filter=status_filter,
        report_type=report_type,
        report_view=report_view,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    return templates.TemplateResponse(
        request,
        'client_reports.html',
        {
            'request': request,
            'current_user': current_user,
            'selected_empresa_id': scope.empresa_id,
            'is_admin_client_preview': current_user.role == 'admin',
            'api_endpoints': _report_api_params(
                request=request,
                base_path='/reports/api',
                empresa_id=scope.empresa_id,
            ),
            'report_actions': _build_report_actions(
                request,
                selected_empresa_id=scope.empresa_id,
            ),
            'allowed_branch_codes': scope.allowed_branch_codes,
            'branch_code': scope.selected_branch_code or '',
            **payload,
        },
    )


def _resolve_report_empresa_for_user(
    *,
    current_user: User,
    db: Session,
    empresa_id: str | None,
    branch_code: str | None,
    start_date: str | None,
    end_date: str | None,
    terminal_code: str | None,
) -> tuple[str, str | None]:
    if current_user.role == 'client':
        scope = _resolve_client_portal_scope(
            current_user=current_user,
            db=db,
            requested_empresa_id=empresa_id,
            requested_branch_code=branch_code,
            start_date=start_date,
            end_date=end_date,
            terminal_code=terminal_code,
        )
        return scope.empresa_id, scope.selected_branch_code
    if 'reports.view' not in ROLE_PERMISSIONS.get(current_user.role, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso negado para relatorios.',
        )
    return empresa_id or settings.control_empresa_id, branch_code


def _build_report_payload_for_api(
    *,
    current_user: User,
    db: Session,
    empresa_id: str | None,
    period_preset: str | None,
    start_date: str | None,
    end_date: str | None,
    start_time: str | None,
    end_time: str | None,
    branch_code: str | None,
    terminal_code: str | None,
    category: str | None,
    product: str | None = None,
    product_code: str | None = None,
    family: str | None = None,
    payment_method: str | None = None,
    card_brand: str | None = None,
    canceled: str | None = None,
    operator: str | None = None,
    customer: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
) -> dict:
    resolved_empresa_id, resolved_branch_code = _resolve_report_empresa_for_user(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    return _build_report_payload(
        empresa_id=resolved_empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=resolved_branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        canceled=canceled,
        operator=operator,
        customer=customer,
        status_filter=status_filter,
        report_type=report_type,
        top_limit=top_limit,
        recent_limit=recent_limit,
    ) | {'selected_empresa_id': resolved_empresa_id}


def _extract_report_api_payload(
    *,
    current_user: User,
    db: Session,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    product: str | None = None,
    product_code: str | None = None,
    family: str | None = None,
    payment_method: str | None = None,
    card_brand: str | None = None,
    canceled: str | None = None,
    operator: str | None = None,
    customer: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
) -> dict:
    return _build_report_payload_for_api(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        product=product,
        product_code=product_code,
        family=family,
        payment_method=payment_method,
        card_brand=card_brand,
        canceled=canceled,
        operator=operator,
        customer=customer,
        status_filter=status_filter,
        report_type=report_type,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )


@router.get('/reports/api/dashboard')
@router.get('/api/reports/dashboard')
def api_reports_dashboard(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 20,
    current_user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    return _extract_report_api_payload(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        status_filter=status_filter,
        report_type=report_type,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )


@router.get('/reports/api/kpis')
@router.get('/api/reports/kpis')
def api_reports_kpis(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    current_user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    payload = _extract_report_api_payload(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        status_filter=status_filter,
        report_type=report_type,
    )
    return {'items': payload['kpi_cards'], 'sync_status': payload['sync_status']}


@router.get('/reports/api/charts')
@router.get('/api/reports/charts')
def api_reports_charts(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    current_user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    payload = _extract_report_api_payload(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        status_filter=status_filter,
        report_type=report_type,
    )
    return {
        'daily_items': payload['daily_items'],
        'top_items': payload['top_items'],
        'type_items': payload['type_items'],
        'payment_items': payload['payment_items'],
        'family_items': payload['family_items'],
    }


@router.get('/reports/api/table')
@router.get('/api/reports/table')
def api_reports_table(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    report_type: str | None = None,
    recent_limit: int = 20,
    current_user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    payload = _extract_report_api_payload(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        status_filter=status_filter,
        report_type=report_type,
        recent_limit=recent_limit,
    )
    return {'items': payload['recent_items'], 'limit': payload['recent_limit']}


@router.get('/reports/api/sync-status')
@router.get('/api/reports/sync-status')
def api_reports_sync_status(
    empresa_id: str | None = None,
    current_user: User = Depends(require_web_user),
    db: Session = Depends(get_db),
):
    resolved_empresa_id, _ = _resolve_report_empresa_for_user(
        current_user=current_user,
        db=db,
        empresa_id=empresa_id,
        branch_code=None,
        start_date=None,
        end_date=None,
        terminal_code=None,
    )
    return _build_sync_status(resolved_empresa_id) | {'empresa_id': resolved_empresa_id}


@router.get('/reports/api/export/csv')
@router.get('/api/reports/export/csv')
@router.get('/reports/export.csv')
def export_reports_csv(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    recent_limit: int = 50,
    _: object = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        top_limit=10,
        recent_limit=recent_limit,
    )
    csv_text = report_recent_sales_to_csv(payload['recent_items'])
    return Response(
        content=csv_text,
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename=reports.csv'},
    )


@router.get('/reports/api/export/excel')
@router.get('/api/reports/export/excel')
@router.get('/reports/export.xlsx')
def export_reports_xlsx(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    _: object = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
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


@router.get('/reports/api/export/pdf')
@router.get('/api/reports/export/pdf')
@router.get('/reports/export.pdf')
def export_reports_pdf(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    _: object = Depends(require_web_permission('reports.view')),
):
    payload = _build_report_payload(
        empresa_id=empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    pdf_bytes = report_to_pdf_bytes(
        payload['overview'],
        payload['daily_items'],
        payload['top_items'],
        payload['recent_items'],
        payload['payment_items'],
        build_report_pdf_summary(
            overview=payload['overview'],
            product_rows=payload['top_items'],
            payment_rows=payload['payment_items'],
        ),
        title='Relatorios administrativos',
    )
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=reports.pdf'},
    )


@router.get('/client/reports/export.csv')
def export_client_reports_csv(
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    recent_limit: int = 50,
    current_user: User = Depends(require_client_portal_access),
    db: Session = Depends(get_db),
):
    scope = _resolve_client_portal_scope(
        current_user=current_user,
        db=db,
        requested_empresa_id=empresa_id,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
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
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    current_user: User = Depends(require_client_portal_access),
    db: Session = Depends(get_db),
):
    scope = _resolve_client_portal_scope(
        current_user=current_user,
        db=db,
        requested_empresa_id=empresa_id,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
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
    request: Request,
    empresa_id: str | None = None,
    period_preset: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    category: str | None = None,
    top_limit: int = 10,
    recent_limit: int = 50,
    current_user: User = Depends(require_client_portal_access),
    db: Session = Depends(get_db),
):
    scope = _resolve_client_portal_scope(
        current_user=current_user,
        db=db,
        requested_empresa_id=empresa_id,
        requested_branch_code=branch_code,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        period_preset=period_preset,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        category=category,
        **_advanced_report_params(request),
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    pdf_bytes = report_to_pdf_bytes(
        payload['overview'],
        payload['daily_items'],
        payload['top_items'],
        payload['recent_items'],
        payload['payment_items'],
        build_report_pdf_summary(
            overview=payload['overview'],
            product_rows=payload['top_items'],
            payment_rows=payload['payment_items'],
        ),
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
    fleet_overview = _remote_client_fleet_overview(fleet_summary)
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
            'fleet_overview': fleet_overview,
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
    latest_log = logs[0] if logs else {}
    client_health = _remote_client_health_snapshot(client_data)
    client_overview = {
        'status': client_data.get('status', '-'),
        'last_seen_at': client_data.get('last_seen_at', '-'),
        'last_sync_at': client_data.get('last_sync_at', '-'),
        'last_command_poll_at': client_data.get('last_command_poll_at', '-'),
        'last_event_type': latest_log.get('event_type', '-'),
        'last_correlation_id': latest_log.get('correlation_id', '-'),
    }
    return templates.TemplateResponse(
        request,
        'connected_api_detail.html',
        {
            'request': request,
            'current_user': current_user,
            'client_data': client_data,
            'logs': logs,
            'client_health': client_health,
            'client_overview': client_overview,
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
    sync_jobs = control.fetch_sync_jobs(limit=50)
    source_status_snapshot = _source_status_snapshot(source_configs, sync_jobs)
    source_execution_overview = _source_execution_overview(source_status_snapshot)
    try:
        remote_agent_snapshot = RemoteAgentService(db).build_status_snapshot()
    except Exception:
        remote_agent_snapshot = {
            'service': 'sync-admin',
            'hostname': '-',
            'last_sync_at': None,
            'last_sync_status': '-',
            'last_sync_reason': '-',
            'last_registration_at': None,
            'last_command_poll_at': None,
            'last_command_origin': '-',
            'pending_local_batches': 0,
            'total_local_records': 0,
        }
    remote_agent_operational = _remote_agent_operational_snapshot(remote_agent_snapshot)
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
    try:
        produto_de_para_rows = control.fetch_produto_de_para(
            empresa_id=settings.control_empresa_id,
            limit=50,
        )
    except Exception:
        produto_de_para_rows = []
    try:
        produtos_sem_de_para = control.fetch_produtos_sem_de_para(
            empresa_id=settings.control_empresa_id,
            limit=50,
        )
    except Exception:
        produtos_sem_de_para = []
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
            'source_execution_overview': source_execution_overview,
            'remote_agent_snapshot': remote_agent_snapshot,
            'remote_agent_operational': remote_agent_operational,
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
            'produto_de_para_rows': produto_de_para_rows,
            'produtos_sem_de_para': produtos_sem_de_para,
        },
    )


@router.get('/settings/company-branches')
def settings_company_branches(
    empresa_id: str,
    _: object = Depends(require_web_permission('settings.view')),
):
    branch_codes = ControlService().fetch_report_branch_options(empresa_id=empresa_id)
    return JSONResponse({'empresa_id': empresa_id, 'items': branch_codes})


@router.get('/settings/xd-mapping')
def settings_xd_mapping(
    _: object = Depends(require_web_permission('settings.view')),
):
    try:
        from agent_local.config.settings import get_agent_settings
        from agent_local.db.mariadb_client import MariaDBClient

        agent_settings = get_agent_settings()
        snapshot = MariaDBClient(
            agent_settings.mariadb_url,
            source_query=agent_settings.source_query,
        ).inspect_xd_mapping()
        return JSONResponse(snapshot)
    except Exception as exc:
        return JSONResponse(
            {
                'status': 'error',
                'error': str(exc),
                'source_kind': '-',
                'tables_present': [],
                'has_salesdocumentsreportview': False,
                'has_documents_fallback': False,
                'reference_tables': {},
            },
            status_code=200,
        )


@router.get('/settings/xd-mapping/routes')
def settings_xd_mapping_routes(
    _: object = Depends(require_web_permission('settings.view')),
):
    return JSONResponse(
        {
            'source_reference': 'TABELAS DO BANCO XD/REFERENCIA TABELAS BD XD SOFTWARE.xlsx',
            'agent_source_query': 'AGENT_SOURCE_QUERY=auto',
            'preferred_source': 'salesdocumentsreportview',
            'fallback_source': 'Documentsbodys + Documentsheaders',
            'local_diagnostic_routes': [
                '/settings/xd-mapping',
                '/settings/xd-mapping/routes',
            ],
            'central_report_routes': [
                '/admin/tenants/{empresa_id}/reports/overview',
                '/admin/tenants/{empresa_id}/reports/daily-sales',
                '/admin/tenants/{empresa_id}/reports/top-products',
                '/admin/tenants/{empresa_id}/reports/breakdown',
                '/admin/tenants/{empresa_id}/reports/recent-sales',
            ],
            'important_xd_tables': [
                'salesdocumentsreportview',
                'Documentsbodys',
                'Documentsheaders',
                'Invoicepaymentdetails',
                'Xconfigpaymenttypes',
                'Itemsgroups',
                'Items',
                'Entities',
            ],
        }
    )


def _produto_de_para_payload(
    *,
    cnpj: str | None,
    codigo_produto_local: str | None = None,
    codigo_produto_web: str | None,
    descricao_produto_local: str | None,
    descricao_produto_web: str | None,
    familia_local: str | None,
    familia_web: str | None,
    categoria_local: str | None,
    categoria_web: str | None,
    ativo: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        'cnpj': cnpj,
        'codigo_produto_web': codigo_produto_web,
        'descricao_produto_local': descricao_produto_local,
        'descricao_produto_web': descricao_produto_web,
        'familia_local': familia_local,
        'familia_web': familia_web,
        'categoria_local': categoria_local,
        'categoria_web': categoria_web,
        'ativo': ativo != 'false',
    }
    if codigo_produto_local is not None:
        payload['codigo_produto_local'] = codigo_produto_local
    return {key: value for key, value in payload.items() if value not in (None, '')}


@router.post('/settings/produto-de-para')
def settings_create_produto_de_para(
    request: Request,
    empresa_id: str = Form(...),
    cnpj: str | None = Form(None),
    codigo_produto_local: str = Form(...),
    codigo_produto_web: str | None = Form(None),
    descricao_produto_local: str | None = Form(None),
    descricao_produto_web: str | None = Form(None),
    familia_local: str | None = Form(None),
    familia_web: str | None = Form(None),
    categoria_local: str | None = Form(None),
    categoria_web: str | None = Form(None),
    ativo: str | None = Form('true'),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    try:
        ControlService().create_produto_de_para(
            empresa_id=empresa_id,
            actor=current_user.username,
            payload=_produto_de_para_payload(
                cnpj=cnpj,
                codigo_produto_local=codigo_produto_local,
                codigo_produto_web=codigo_produto_web,
                descricao_produto_local=descricao_produto_local,
                descricao_produto_web=descricao_produto_web,
                familia_local=familia_local,
                familia_web=familia_web,
                categoria_local=categoria_local,
                categoria_web=categoria_web,
                ativo=ativo,
            ),
        )
        return RedirectResponse(
            '/settings?flash=DE/PARA+de+produto+salvo',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+salvar+DE/PARA:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/produto-de-para/{mapping_id}')
def settings_update_produto_de_para(
    mapping_id: int,
    empresa_id: str = Form(...),
    cnpj: str | None = Form(None),
    codigo_produto_web: str | None = Form(None),
    descricao_produto_local: str | None = Form(None),
    descricao_produto_web: str | None = Form(None),
    familia_local: str | None = Form(None),
    familia_web: str | None = Form(None),
    categoria_local: str | None = Form(None),
    categoria_web: str | None = Form(None),
    ativo: str | None = Form('true'),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    try:
        ControlService().update_produto_de_para(
            empresa_id=empresa_id,
            mapping_id=mapping_id,
            actor=current_user.username,
            payload=_produto_de_para_payload(
                cnpj=cnpj,
                codigo_produto_web=codigo_produto_web,
                descricao_produto_local=descricao_produto_local,
                descricao_produto_web=descricao_produto_web,
                familia_local=familia_local,
                familia_web=familia_web,
                categoria_local=categoria_local,
                categoria_web=categoria_web,
                ativo=ativo,
            ),
        )
        return RedirectResponse(
            '/settings?flash=DE/PARA+de+produto+atualizado',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+atualizar+DE/PARA:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


@router.post('/settings/produto-de-para/{mapping_id}/delete')
def settings_delete_produto_de_para(
    mapping_id: int,
    empresa_id: str = Form(...),
    current_user: User = Depends(require_web_permission('settings.manage')),
):
    try:
        ControlService().delete_produto_de_para(
            empresa_id=empresa_id,
            mapping_id=mapping_id,
            actor=current_user.username,
        )
        return RedirectResponse(
            '/settings?flash=DE/PARA+de+produto+removido',
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as exc:
        return RedirectResponse(
            f'/settings?error=Falha+ao+remover+DE/PARA:+{quote_plus(str(exc))}',
            status_code=status.HTTP_302_FOUND,
        )


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
