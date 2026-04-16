from __future__ import annotations

from dataclasses import dataclass
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

    def provision_tenant(self, empresa_id: str, nome: str, actor: str | None = None) -> str:
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
        return data['api_key']

    def rotate_tenant_key(self, empresa_id: str, actor: str | None = None) -> str:
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
        return data['api_key']

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
                    'last_status': item.get('last_status', '-'),
                    'last_error': item.get('last_error', '-'),
                }
            )
        return rows

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
        actor: str | None = None,
    ) -> dict:
        payload = {
            'ingestion_enabled': ingestion_enabled,
            'max_batch_size': max_batch_size,
            'retention_mode': retention_mode,
            'retention_months': retention_months,
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
