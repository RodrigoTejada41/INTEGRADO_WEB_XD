from datetime import UTC, datetime
from threading import Lock


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self.sync_batches_total = 0
        self.sync_records_inserted_total = 0
        self.sync_records_updated_total = 0
        self.sync_failures_total = 0
        self.retention_processed_total = 0
        self.tenant_scheduler_runs_total = 0
        self.tenant_scheduler_failures_total = 0
        self.last_sync_epoch_by_empresa: dict[str, int] = {}
        self.last_tenant_scheduler_epoch_by_empresa: dict[str, int] = {}

    def record_sync_success(
        self,
        empresa_id: str,
        inserted_count: int,
        updated_count: int,
    ) -> None:
        with self._lock:
            self.sync_batches_total += 1
            self.sync_records_inserted_total += inserted_count
            self.sync_records_updated_total += updated_count
            self.last_sync_epoch_by_empresa[empresa_id] = int(datetime.now(UTC).timestamp())

    def record_sync_failure(self) -> None:
        with self._lock:
            self.sync_failures_total += 1

    def record_retention(self, processed: int) -> None:
        with self._lock:
            self.retention_processed_total += processed

    def record_tenant_scheduler_success(self, empresa_id: str) -> None:
        with self._lock:
            self.tenant_scheduler_runs_total += 1
            self.last_tenant_scheduler_epoch_by_empresa[empresa_id] = int(
                datetime.now(UTC).timestamp()
            )

    def record_tenant_scheduler_failure(self) -> None:
        with self._lock:
            self.tenant_scheduler_failures_total += 1

    def render_prometheus(self) -> str:
        lines = [
            "# HELP sync_batches_total Total de lotes de sincronizacao processados com sucesso.",
            "# TYPE sync_batches_total counter",
            f"sync_batches_total {self.sync_batches_total}",
            "# HELP sync_records_inserted_total Total de registros inseridos por sync.",
            "# TYPE sync_records_inserted_total counter",
            f"sync_records_inserted_total {self.sync_records_inserted_total}",
            "# HELP sync_records_updated_total Total de registros atualizados por sync.",
            "# TYPE sync_records_updated_total counter",
            f"sync_records_updated_total {self.sync_records_updated_total}",
            "# HELP sync_failures_total Total de falhas de sincronizacao.",
            "# TYPE sync_failures_total counter",
            f"sync_failures_total {self.sync_failures_total}",
            "# HELP retention_processed_total Total de registros processados na retencao.",
            "# TYPE retention_processed_total counter",
            f"retention_processed_total {self.retention_processed_total}",
            "# HELP tenant_scheduler_runs_total Total de execucoes do scheduler por tenant.",
            "# TYPE tenant_scheduler_runs_total counter",
            f"tenant_scheduler_runs_total {self.tenant_scheduler_runs_total}",
            "# HELP tenant_scheduler_failures_total Total de falhas do scheduler por tenant.",
            "# TYPE tenant_scheduler_failures_total counter",
            f"tenant_scheduler_failures_total {self.tenant_scheduler_failures_total}",
            "# HELP sync_last_success_epoch Timestamp epoch do ultimo sync por empresa.",
            "# TYPE sync_last_success_epoch gauge",
        ]
        for empresa_id, epoch in sorted(self.last_sync_epoch_by_empresa.items()):
            lines.append(f'sync_last_success_epoch{{empresa_id="{empresa_id}"}} {epoch}')
        lines.append("# HELP tenant_scheduler_last_success_epoch Timestamp epoch da ultima execucao do scheduler por empresa.")
        lines.append("# TYPE tenant_scheduler_last_success_epoch gauge")
        for empresa_id, epoch in sorted(self.last_tenant_scheduler_epoch_by_empresa.items()):
            lines.append(f'tenant_scheduler_last_success_epoch{{empresa_id="{empresa_id}"}} {epoch}')
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
