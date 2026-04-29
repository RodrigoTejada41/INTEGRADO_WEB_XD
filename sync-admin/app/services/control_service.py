from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

import httpx

from app.config.settings import settings


@dataclass
class ControlSummary:
    api_health: str
    sync_batches_total: float
    sync_records_inserted_total: float
    sync_records_updated_total: float
    sync_application_failures_total: float
    preflight_connection_errors_total: float
    retention_processed_total: float
    tenant_destination_delivery_total: float
    tenant_destination_delivery_failed_total: float


@dataclass
class AuditSummary:
    empresa_id: str
    total_count: float
    success_count: float
    failure_count: float
    actors: list[str]
    actions: list[str]


@dataclass
class SyncJobsSummary:
    empresa_id: str
    pending_count: float
    processing_count: float
    done_count: float
    dead_letter_count: float
    failed_count: float


@dataclass
class TenantObservabilitySummary:
    empresa_id: str
    sync_batches_total: float
    sync_failures_total: float
    tenant_scheduler_runs_total: float
    tenant_queue_processed_total: float
    tenant_queue_failed_total: float
    tenant_queue_retried_total: float
    tenant_queue_dead_letter_total: float
    tenant_destination_delivery_total: float
    tenant_destination_delivery_failed_total: float
    sync_last_success_lag_seconds: float
    tenant_scheduler_last_success_lag_seconds: float
    tenant_queue_last_event_lag_seconds: float
    tenant_destination_last_event_lag_seconds: float


@dataclass
class SourceCycleSummary:
    empresa_id: str
    total_count: int
    active_count: int
    due_count: int
    overdue_count: int
    next_run_at: str
    last_success_at: str
    last_success_lag_seconds: float


@dataclass
class SourceJobSummary:
    id: str
    empresa_id: str
    source_config_id: str
    status: str
    attempts: int
    scheduled_at: str
    next_run_at: str
    started_at: str
    finished_at: str
    dead_letter_at: str
    dead_letter_reason: str
    last_error: str
    created_at: str
    updated_at: str


@dataclass
class RemoteClientFleetSummary:
    total_clients: int
    online_clients: int
    error_clients: int
    unique_empresas: int


class ControlService:
    def __init__(self) -> None:
        self.base_url = settings.control_api_base_url.rstrip('/')
        self.admin_headers = {'X-Admin-Token': settings.control_admin_token}

    def fetch_summary(self) -> ControlSummary:
        api_health = 'offline'
        metrics_text = ''
        with httpx.Client(timeout=10.0) as client:
            try:
                health_resp = client.get(f'{self.base_url}/health')
                if health_resp.status_code == 200:
                    api_health = 'online'
            except Exception:
                api_health = 'offline'

            try:
                metrics_resp = client.get(f'{self.base_url}/metrics')
                if metrics_resp.status_code == 200:
                    metrics_text = metrics_resp.text
            except Exception:
                metrics_text = ''

        metrics = self._parse_metrics(metrics_text)
        preflight_connection_errors_total = float(self._count_preflight_connection_errors())
        return ControlSummary(
            api_health=api_health,
            sync_batches_total=metrics.get('sync_batches_total', 0.0),
            sync_records_inserted_total=metrics.get('sync_records_inserted_total', 0.0),
            sync_records_updated_total=metrics.get('sync_records_updated_total', 0.0),
            sync_application_failures_total=metrics.get('sync_failures_total', 0.0),
            preflight_connection_errors_total=preflight_connection_errors_total,
            retention_processed_total=metrics.get('retention_processed_total', 0.0),
            tenant_destination_delivery_total=metrics.get('tenant_destination_delivery_total', 0.0),
            tenant_destination_delivery_failed_total=metrics.get(
                'tenant_destination_delivery_failed_total', 0.0
            ),
        )

    def provision_tenant(self, empresa_id: str, nome: str, actor: str | None = None) -> dict:
        payload = {'empresa_id': empresa_id, 'nome': nome}
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants',
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return {
            'api_key': data['api_key'],
            'api_key_last_rotated_at': data.get('api_key_last_rotated_at'),
            'api_key_expires_at': data.get('api_key_expires_at'),
        }

    def rotate_tenant_key(self, empresa_id: str, actor: str | None = None) -> dict:
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{empresa_id}/rotate-key',
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        return {
            'api_key': data['api_key'],
            'api_key_last_rotated_at': data.get('api_key_last_rotated_at'),
            'api_key_expires_at': data.get('api_key_expires_at'),
        }

    def trigger_source_sync(
        self,
        config_id: str,
        *,
        empresa_id: str | None = None,
        actor: str | None = None,
    ) -> dict:
        target_empresa = empresa_id or settings.control_empresa_id
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{target_empresa}/source-configs/{config_id}/sync',
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        return {
            'id': data.get('id'),
            'empresa_id': data.get('empresa_id'),
            'nome': data.get('nome'),
            'connector_type': data.get('connector_type'),
            'sync_interval_minutes': data.get('sync_interval_minutes'),
            'ativo': data.get('ativo'),
            'last_run_at': data.get('last_run_at'),
            'last_scheduled_at': data.get('last_scheduled_at'),
            'next_run_at': data.get('next_run_at'),
            'last_status': data.get('last_status'),
            'last_error': data.get('last_error'),
        }

    def trigger_all_source_sync(self, empresa_id: str | None = None, actor: str | None = None) -> dict:
        target_empresa = empresa_id or settings.control_empresa_id
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{target_empresa}/source-configs/sync-all',
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        return {
            'empresa_id': data.get('empresa_id', target_empresa),
            'scope': data.get('scope', 'source'),
            'total_count': int(data.get('total_count', 0)),
            'active_count': int(data.get('active_count', 0)),
            'inactive_count': int(data.get('inactive_count', 0)),
            'pending_count': int(data.get('pending_count', 0)),
            'ok_count': int(data.get('ok_count', 0)),
            'failed_count': int(data.get('failed_count', 0)),
            'retrying_count': int(data.get('retrying_count', 0)),
            'dead_letter_count': int(data.get('dead_letter_count', 0)),
            'connector_types': list(data.get('connector_types', [])),
        }

    def update_agent_key_file(self, api_key: str) -> str:
        file_path = Path(settings.agent_api_key_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(api_key.strip(), encoding='utf-8')
        return str(file_path)

    def recent_agent_errors(self, limit: int = 20) -> list[dict]:
        file_path = Path(settings.agent_audit_file)
        if not file_path.exists():
            return []
        lines = file_path.read_text(encoding='utf-8').splitlines()
        rows: list[dict] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            level = str(payload.get('level', '')).lower()
            if level != 'error':
                continue
            rows.append(
                {
                    'timestamp': payload.get('timestamp', '-'),
                    'source': 'agent',
                    'event': payload.get('event', '-'),
                    'detail': json.dumps(payload.get('context', {}), ensure_ascii=True),
                }
            )
            if len(rows) >= limit:
                break
        return rows

    def api_error_snapshot(self) -> dict:
        summary = self.fetch_summary()
        return {
            'timestamp': '-',
            'source': 'api',
            'event': 'sync_application_failures_total',
            'detail': f"current_value={summary.sync_application_failures_total}",
        }

    def fetch_sync_jobs_summary(self) -> SyncJobsSummary:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/sync-jobs/summary',
                    headers=self.admin_headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return SyncJobsSummary(
                empresa_id=settings.control_empresa_id,
                pending_count=0.0,
                processing_count=0.0,
                done_count=0.0,
                dead_letter_count=0.0,
                failed_count=0.0,
            )
        return SyncJobsSummary(
            empresa_id=data['empresa_id'],
            pending_count=float(data['pending_count']),
            processing_count=float(data['processing_count']),
            done_count=float(data['done_count']),
            dead_letter_count=float(data['dead_letter_count']),
            failed_count=float(data['failed_count']),
        )

    def fetch_dead_letter_jobs(self, limit: int = 10) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/sync-jobs/dead-letter',
                    headers=self.admin_headers,
                    params={'limit': limit},
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        rows: list[dict] = []
        for item in data:
            rows.append(
                {
                    'id': item.get('id', '-'),
                    'empresa_id': item.get('empresa_id', '-'),
                    'source_config_id': item.get('source_config_id', '-'),
                    'status': item.get('status', '-'),
                    'attempts': item.get('attempts', 0),
                    'next_run_at': item.get('next_run_at', '-'),
                    'last_error': item.get('last_error', '-'),
                    'dead_letter_reason': item.get('dead_letter_reason', '-'),
                }
            )
        return rows

    def retry_sync_job(self, job_id: str) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/sync-jobs/{job_id}/retry',
                headers=self.admin_headers,
            )
            response.raise_for_status()
            return response.json()

    def fetch_destination_configs(self) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/destination-configs',
                    headers=self.admin_headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        rows: list[dict] = []
        for item in data:
            rows.append(
                {
                    'id': item.get('id', '-'),
                    'empresa_id': item.get('empresa_id', '-'),
                    'nome': item.get('nome', '-'),
                    'connector_type': item.get('connector_type', '-'),
                    'sync_interval_minutes': item.get('sync_interval_minutes', 0),
                    'ativo': item.get('ativo', False),
                    'last_run_at': item.get('last_run_at', '-'),
                    'last_scheduled_at': item.get('last_scheduled_at', '-'),
                    'next_run_at': item.get('next_run_at', '-'),
                    'last_status': item.get('last_status', '-'),
                    'last_error': item.get('last_error', '-'),
                    'settings': item.get('settings', {}),
                }
            )
        return rows

    def fetch_source_cycle_summary(self, source_configs: list[dict] | None = None) -> SourceCycleSummary:
        configs = source_configs if source_configs is not None else self.fetch_source_configs()
        now = datetime.now(UTC)
        active_configs = [item for item in configs if item.get('ativo', False)]
        due_count = 0
        overdue_count = 0
        next_run_candidates: list[datetime] = []
        success_candidates: list[datetime] = []

        for item in active_configs:
            next_run_at = self._parse_timestamp(item.get('next_run_at'))
            last_run_at = self._parse_timestamp(item.get('last_run_at'))
            if next_run_at is not None:
                next_run_candidates.append(next_run_at)
                if next_run_at <= now:
                    due_count += 1
                if next_run_at < now:
                    overdue_count += 1
            if item.get('last_status') == 'ok' and last_run_at is not None:
                success_candidates.append(last_run_at)

        next_run_at_value = min(next_run_candidates) if next_run_candidates else None
        last_success_at_value = max(success_candidates) if success_candidates else None
        last_success_lag_seconds = 0.0
        if last_success_at_value is not None:
            last_success_lag_seconds = max(0.0, (now - last_success_at_value).total_seconds())

        return SourceCycleSummary(
            empresa_id=settings.control_empresa_id,
            total_count=len(configs),
            active_count=len(active_configs),
            due_count=due_count,
            overdue_count=overdue_count,
            next_run_at=next_run_at_value.isoformat() if next_run_at_value else '-',
            last_success_at=last_success_at_value.isoformat() if last_success_at_value else '-',
            last_success_lag_seconds=last_success_lag_seconds,
        )

    def fetch_source_configs(self) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/source-configs',
                    headers=self.admin_headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        rows: list[dict] = []
        for item in data:
            rows.append(
                {
                    'id': item.get('id', '-'),
                    'empresa_id': item.get('empresa_id', '-'),
                    'nome': item.get('nome', '-'),
                    'connector_type': item.get('connector_type', '-'),
                    'sync_interval_minutes': item.get('sync_interval_minutes', 0),
                    'ativo': item.get('ativo', False),
                    'last_run_at': item.get('last_run_at', '-'),
                    'last_scheduled_at': item.get('last_scheduled_at', '-'),
                    'next_run_at': item.get('next_run_at', '-'),
                    'last_status': item.get('last_status', '-'),
                    'last_error': item.get('last_error', '-'),
                    'settings': item.get('settings', {}),
                }
            )
        return rows

    def fetch_sync_jobs(self, limit: int = 20) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/sync-jobs',
                    headers=self.admin_headers,
                    params={'limit': limit},
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        rows: list[dict] = []
        for item in data:
            rows.append(
                {
                    'id': item.get('id', '-'),
                    'empresa_id': item.get('empresa_id', '-'),
                    'source_config_id': item.get('source_config_id', '-'),
                    'status': item.get('status', '-'),
                    'attempts': int(item.get('attempts', 0)),
                    'scheduled_at': item.get('scheduled_at', '-'),
                    'next_run_at': item.get('next_run_at', '-'),
                    'started_at': item.get('started_at', '-'),
                    'finished_at': item.get('finished_at', '-'),
                    'dead_letter_at': item.get('dead_letter_at', '-'),
                    'dead_letter_reason': item.get('dead_letter_reason', '-'),
                    'last_error': item.get('last_error', '-'),
                    'created_at': item.get('created_at', '-'),
                    'updated_at': item.get('updated_at', '-'),
                }
            )
        return rows

    def fetch_remote_client_summary(
        self,
        *,
        empresa_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> RemoteClientFleetSummary:
        params = {k: v for k, v in {"empresa_id": empresa_id, "status": status, "search": search}.items() if v}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/api/v1/clients/summary',
                    headers=self.admin_headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return RemoteClientFleetSummary(0, 0, 0, 0)
        return RemoteClientFleetSummary(
            total_clients=int(data.get('total_clients', 0)),
            online_clients=int(data.get('online_clients', 0)),
            error_clients=int(data.get('error_clients', 0)),
            unique_empresas=int(data.get('unique_empresas', 0)),
        )

    def fetch_remote_clients(
        self,
        *,
        empresa_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        params = {k: v for k, v in {"empresa_id": empresa_id, "status": status, "search": search}.items() if v}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/api/v1/clients',
                    headers=self.admin_headers,
                    params=params,
                )
                response.raise_for_status()
                return list(response.json())
        except Exception:
            return []

    def fetch_remote_client(self, client_id: str) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f'{self.base_url}/api/v1/clients/{client_id}/config',
                headers=self.admin_headers,
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _parse_timestamp(value: object) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
        return None

    def fetch_remote_client_logs(self, client_id: str, *, limit: int = 20) -> list[dict]:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f'{self.base_url}/api/v1/clients/{client_id}/logs',
                headers=self.admin_headers,
                params={'limit': limit},
            )
            response.raise_for_status()
            return list(response.json())

    def fetch_report_overview(
        self,
        *,
        empresa_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        category: str | None = None,
        product: str | None = None,
        product_code: str | None = None,
        family: str | None = None,
        payment_method: str | None = None,
        card_brand: str | None = None,
        status_filter: str | None = None,
        canceled: str | None = None,
        operator: str | None = None,
        customer: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        params = {
            key: value
            for key, value in {
                'start_date': start_date,
                'end_date': end_date,
                'branch_code': branch_code,
                'terminal_code': terminal_code,
                'category': category,
                'product': product,
                'product_code': product_code,
                'family': family,
                'payment_method': payment_method,
                'card_brand': card_brand,
                'status_filter': status_filter,
                'canceled': canceled,
                'operator': operator,
                'customer': customer,
                'start_time': start_time,
                'end_time': end_time,
            }.items()
            if value
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{empresa_id or settings.control_empresa_id}/reports/overview',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def fetch_report_daily_sales(
        self,
        *,
        empresa_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        category: str | None = None,
        product: str | None = None,
        product_code: str | None = None,
        family: str | None = None,
        payment_method: str | None = None,
        card_brand: str | None = None,
        status_filter: str | None = None,
        canceled: str | None = None,
        operator: str | None = None,
        customer: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        params = {
            key: value
            for key, value in {
                'start_date': start_date,
                'end_date': end_date,
                'branch_code': branch_code,
                'terminal_code': terminal_code,
                'category': category,
                'product': product,
                'product_code': product_code,
                'family': family,
                'payment_method': payment_method,
                'card_brand': card_brand,
                'status_filter': status_filter,
                'canceled': canceled,
                'operator': operator,
                'customer': customer,
                'start_time': start_time,
                'end_time': end_time,
            }.items()
            if value
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{empresa_id or settings.control_empresa_id}/reports/daily-sales',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def fetch_report_top_products(
        self,
        *,
        empresa_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        category: str | None = None,
        product: str | None = None,
        product_code: str | None = None,
        family: str | None = None,
        payment_method: str | None = None,
        card_brand: str | None = None,
        status_filter: str | None = None,
        canceled: str | None = None,
        operator: str | None = None,
        customer: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 10,
    ) -> dict:
        params = {
            key: value
            for key, value in {
                'start_date': start_date,
                'end_date': end_date,
                'branch_code': branch_code,
                'terminal_code': terminal_code,
                'category': category,
                'product': product,
                'product_code': product_code,
                'family': family,
                'payment_method': payment_method,
                'card_brand': card_brand,
                'status_filter': status_filter,
                'canceled': canceled,
                'operator': operator,
                'customer': customer,
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit,
            }.items()
            if value is not None and value != ''
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{empresa_id or settings.control_empresa_id}/reports/top-products',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def fetch_report_breakdown(
        self,
        *,
        group_by: str,
        empresa_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        category: str | None = None,
        product: str | None = None,
        product_code: str | None = None,
        family: str | None = None,
        payment_method: str | None = None,
        card_brand: str | None = None,
        status_filter: str | None = None,
        canceled: str | None = None,
        operator: str | None = None,
        customer: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 10,
    ) -> dict:
        params = {
            key: value
            for key, value in {
                'group_by': group_by,
                'start_date': start_date,
                'end_date': end_date,
                'branch_code': branch_code,
                'terminal_code': terminal_code,
                'category': category,
                'product': product,
                'product_code': product_code,
                'family': family,
                'payment_method': payment_method,
                'card_brand': card_brand,
                'status_filter': status_filter,
                'canceled': canceled,
                'operator': operator,
                'customer': customer,
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit,
            }.items()
            if value is not None and value != ''
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{empresa_id or settings.control_empresa_id}/reports/breakdown',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def fetch_report_recent_sales(
        self,
        *,
        empresa_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        branch_code: str | None = None,
        terminal_code: str | None = None,
        category: str | None = None,
        product: str | None = None,
        product_code: str | None = None,
        family: str | None = None,
        payment_method: str | None = None,
        card_brand: str | None = None,
        status_filter: str | None = None,
        canceled: str | None = None,
        operator: str | None = None,
        customer: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20,
    ) -> dict:
        params = {
            key: value
            for key, value in {
                'start_date': start_date,
                'end_date': end_date,
                'branch_code': branch_code,
                'terminal_code': terminal_code,
                'category': category,
                'product': product,
                'product_code': product_code,
                'family': family,
                'payment_method': payment_method,
                'card_brand': card_brand,
                'status_filter': status_filter,
                'canceled': canceled,
                'operator': operator,
                'customer': customer,
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit,
            }.items()
            if value is not None and value != ''
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{empresa_id or settings.control_empresa_id}/reports/recent-sales',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def fetch_report_branch_options(
        self,
        *,
        empresa_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        terminal_code: str | None = None,
    ) -> list[str]:
        params = {
            key: value
            for key, value in {
                'start_date': start_date,
                'end_date': end_date,
                'terminal_code': terminal_code,
            }.items()
            if value
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{empresa_id or settings.control_empresa_id}/reports/branches',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        return [str(item) for item in data.get('items', [])]

    def fetch_produto_de_para(
        self,
        *,
        empresa_id: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        target_empresa = empresa_id or settings.control_empresa_id
        params = {'limit': max(1, min(limit, 500)), 'offset': max(offset, 0)}
        if search:
            params['search'] = search
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{target_empresa}/produto-de-para',
                headers=self.admin_headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        return list(data.get('items', []))

    def fetch_produtos_sem_de_para(
        self,
        *,
        empresa_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        target_empresa = empresa_id or settings.control_empresa_id
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f'{self.base_url}/admin/tenants/{target_empresa}/produto-de-para/unmapped',
                headers=self.admin_headers,
                params={'limit': max(1, min(limit, 500))},
            )
            response.raise_for_status()
            data = response.json()
        return list(data.get('items', []))

    def create_produto_de_para(
        self,
        *,
        empresa_id: str | None = None,
        payload: dict,
        actor: str | None = None,
    ) -> dict:
        target_empresa = empresa_id or settings.control_empresa_id
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{target_empresa}/produto-de-para',
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def update_produto_de_para(
        self,
        *,
        empresa_id: str | None = None,
        mapping_id: int,
        payload: dict,
        actor: str | None = None,
    ) -> dict:
        target_empresa = empresa_id or settings.control_empresa_id
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.put(
                f'{self.base_url}/admin/tenants/{target_empresa}/produto-de-para/{mapping_id}',
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def delete_produto_de_para(
        self,
        *,
        empresa_id: str | None = None,
        mapping_id: int,
        actor: str | None = None,
    ) -> dict:
        target_empresa = empresa_id or settings.control_empresa_id
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.delete(
                f'{self.base_url}/admin/tenants/{target_empresa}/produto-de-para/{mapping_id}',
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def queue_remote_force_sync(self, client_id: str, *, actor: str | None = None) -> dict:
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f'{self.base_url}/api/v1/clients/{client_id}/sync',
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def queue_remote_config_update(
        self,
        client_id: str,
        *,
        payload: dict[str, object],
        actor: str | None = None,
    ) -> dict:
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f'{self.base_url}/api/v1/clients/{client_id}/config',
                headers=headers,
                json={'payload': payload},
            )
            response.raise_for_status()
            return response.json()

    def fetch_tenant_observability(self, empresa_id: str | None = None) -> TenantObservabilitySummary:
        target_empresa = empresa_id or settings.control_empresa_id
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{target_empresa}/observability',
                    headers=self.admin_headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return TenantObservabilitySummary(
                empresa_id=target_empresa,
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
        return TenantObservabilitySummary(
            empresa_id=str(data.get("empresa_id", target_empresa)),
            sync_batches_total=float(data.get("sync_batches_total", 0)),
            sync_failures_total=float(data.get("sync_failures_total", 0)),
            tenant_scheduler_runs_total=float(data.get("tenant_scheduler_runs_total", 0)),
            tenant_queue_processed_total=float(data.get("tenant_queue_processed_total", 0)),
            tenant_queue_failed_total=float(data.get("tenant_queue_failed_total", 0)),
            tenant_queue_retried_total=float(data.get("tenant_queue_retried_total", 0)),
            tenant_queue_dead_letter_total=float(data.get("tenant_queue_dead_letter_total", 0)),
            tenant_destination_delivery_total=float(data.get("tenant_destination_delivery_total", 0)),
            tenant_destination_delivery_failed_total=float(
                data.get("tenant_destination_delivery_failed_total", 0)
            ),
            sync_last_success_lag_seconds=float(data.get("sync_last_success_lag_seconds", 0)),
            tenant_scheduler_last_success_lag_seconds=float(
                data.get("tenant_scheduler_last_success_lag_seconds", 0)
            ),
            tenant_queue_last_event_lag_seconds=float(data.get("tenant_queue_last_event_lag_seconds", 0)),
            tenant_destination_last_event_lag_seconds=float(
                data.get("tenant_destination_last_event_lag_seconds", 0)
            ),
        )

    def get_server_settings(self) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f'{self.base_url}/admin/server-settings',
                headers=self.admin_headers,
            )
            response.raise_for_status()
            return response.json()

    def update_server_settings(
        self,
        *,
        ingestion_enabled: bool,
        max_batch_size: int,
        retention_mode: str,
        retention_months: int,
        connection_secrets_file: str,
        actor: str | None = None,
    ) -> dict:
        payload = {
            'ingestion_enabled': ingestion_enabled,
            'max_batch_size': max_batch_size,
            'retention_mode': retention_mode,
            'retention_months': retention_months,
            'connection_secrets_file': connection_secrets_file,
        }
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=15.0) as client:
            response = client.put(
                f'{self.base_url}/admin/server-settings',
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def create_secure_connection_config(
        self,
        *,
        scope: str,
        nome: str,
        connector_type: str,
        sync_interval_minutes: int,
        settings: dict[str, str],
        secret_settings: dict[str, str],
        generate_access_key: bool,
        access_key_field: str | None = None,
        actor: str | None = None,
    ) -> dict:
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        payload = {
            'scope': scope,
            'nome': nome,
            'connector_type': connector_type,
            'sync_interval_minutes': sync_interval_minutes,
            'settings': settings,
            'secret_settings': secret_settings,
            'generate_access_key': generate_access_key,
            'access_key_field': access_key_field,
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/secure-configs',
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def rotate_secure_connection_key(
        self,
        *,
        settings_key: str,
        access_key_field: str | None = None,
        actor: str | None = None,
    ) -> dict:
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/secure-configs/{settings_key}/rotate-key',
                headers=headers,
                json={'access_key_field': access_key_field},
            )
            response.raise_for_status()
            return response.json()

    def update_secure_connection_secret(
        self,
        *,
        settings_key: str,
        secret_settings: dict[str, str],
        merge: bool = True,
        actor: str | None = None,
    ) -> dict:
        headers = dict(self.admin_headers)
        if actor:
            headers['X-Audit-Actor'] = actor
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/secure-configs/{settings_key}/update-secret',
                headers=headers,
                json={'secret_settings': secret_settings, 'merge': merge},
            )
            response.raise_for_status()
            return response.json()

    def fetch_audit_summary(self) -> AuditSummary:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/audit/summary',
                    headers=self.admin_headers,
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return AuditSummary(
                empresa_id=settings.control_empresa_id,
                total_count=0.0,
                success_count=0.0,
                failure_count=0.0,
                actors=[],
                actions=[],
            )
        return AuditSummary(
            empresa_id=data['empresa_id'],
            total_count=float(data['total_count']),
            success_count=float(data['success_count']),
            failure_count=float(data['failure_count']),
            actors=[str(item) for item in data.get('actors', [])],
            actions=[str(item) for item in data.get('actions', [])],
        )

    def fetch_audit_events(self, limit: int = 10) -> list[dict]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f'{self.base_url}/admin/tenants/{settings.control_empresa_id}/audit/events',
                    headers=self.admin_headers,
                    params={'limit': limit},
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []
        rows: list[dict] = []
        for item in data:
            rows.append(
                {
                    'id': item.get('id', '-'),
                    'empresa_id': item.get('empresa_id', '-'),
                    'actor': item.get('actor', '-'),
                    'action': item.get('action', '-'),
                    'resource_type': item.get('resource_type', '-'),
                    'resource_id': item.get('resource_id', '-'),
                    'status': item.get('status', '-'),
                    'correlation_id': item.get('correlation_id', '-'),
                    'request_path': item.get('request_path', '-'),
                    'actor_ip': item.get('actor_ip', '-'),
                    'user_agent': item.get('user_agent', '-'),
                    'detail': item.get('detail', {}),
                    'created_at': item.get('created_at', '-'),
                }
            )
        return rows

    @staticmethod
    def _parse_metrics(metrics_text: str) -> dict[str, float]:
        result: dict[str, float] = {}
        for line in metrics_text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '{' in line:
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            metric_name, metric_value = parts
            try:
                result[metric_name] = float(metric_value)
            except ValueError:
                continue
        return result

    def _count_preflight_connection_errors(self) -> int:
        file_path = Path(settings.agent_audit_file)
        if not file_path.exists():
            return 0
        total = 0
        for line in file_path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(payload.get('level', '')).lower() != 'error':
                continue
            if payload.get('event') != 'agent_preflight_failed':
                continue
            context = payload.get('context', {})
            errors = context.get('errors', [])
            if not isinstance(errors, list):
                continue
            for err in errors:
                err_text = str(err).lower()
                if "api:" in err_text and (
                    "connection refused" in err_text
                    or "connect" in err_text
                    or "timed out" in err_text
                    or "name or service not known" in err_text
                ):
                    total += 1
                    break
        return total
