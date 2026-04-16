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
        )

    def provision_tenant(self, empresa_id: str, nome: str) -> str:
        payload = {'empresa_id': empresa_id, 'nome': nome}
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants',
                headers=self.admin_headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data['api_key']

    def rotate_tenant_key(self, empresa_id: str) -> str:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f'{self.base_url}/admin/tenants/{empresa_id}/rotate-key',
                headers=self.admin_headers,
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
    ) -> dict:
        payload = {
            'ingestion_enabled': ingestion_enabled,
            'max_batch_size': max_batch_size,
            'retention_mode': retention_mode,
            'retention_months': retention_months,
        }
        with httpx.Client(timeout=15.0) as client:
            response = client.put(
                f'{self.base_url}/admin/server-settings',
                headers=self.admin_headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

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
