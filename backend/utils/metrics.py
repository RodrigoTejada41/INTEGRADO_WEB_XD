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
        self.tenant_queue_enqueued_total = 0
        self.tenant_queue_processed_total = 0
        self.tenant_queue_failed_total = 0
        self.tenant_queue_retried_total = 0
        self.tenant_queue_dead_letter_total = 0
        self.tenant_destination_delivery_total = 0
        self.tenant_destination_delivery_failed_total = 0
        self.last_sync_epoch_by_empresa: dict[str, int] = {}
        self.last_tenant_scheduler_epoch_by_empresa: dict[str, int] = {}
        self.last_tenant_queue_epoch_by_empresa: dict[str, int] = {}
        self.last_tenant_destination_epoch_by_empresa: dict[str, int] = {}

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

    def record_tenant_queue_enqueue(self, count: int) -> None:
        with self._lock:
            self.tenant_queue_enqueued_total += count

    def record_tenant_queue_processed(self, empresa_id: str) -> None:
        with self._lock:
            self.tenant_queue_processed_total += 1
            self.last_tenant_queue_epoch_by_empresa[empresa_id] = int(datetime.now(UTC).timestamp())

    def record_tenant_queue_failed(self, empresa_id: str) -> None:
        with self._lock:
            self.tenant_queue_failed_total += 1
            self.last_tenant_queue_epoch_by_empresa[empresa_id] = int(datetime.now(UTC).timestamp())

    def record_tenant_queue_retried(self, empresa_id: str) -> None:
        with self._lock:
            self.tenant_queue_retried_total += 1
            self.last_tenant_queue_epoch_by_empresa[empresa_id] = int(datetime.now(UTC).timestamp())

    def record_tenant_queue_dead_letter(self, empresa_id: str) -> None:
        with self._lock:
            self.tenant_queue_dead_letter_total += 1
            self.last_tenant_queue_epoch_by_empresa[empresa_id] = int(datetime.now(UTC).timestamp())

    def record_tenant_destination_delivery(self, empresa_id: str, delivered_count: int) -> None:
        with self._lock:
            self.tenant_destination_delivery_total += delivered_count
            self.last_tenant_destination_epoch_by_empresa[empresa_id] = int(
                datetime.now(UTC).timestamp()
            )

    def record_tenant_destination_failure(self, empresa_id: str) -> None:
        with self._lock:
            self.tenant_destination_delivery_failed_total += 1
            self.last_tenant_destination_epoch_by_empresa[empresa_id] = int(
                datetime.now(UTC).timestamp()
            )

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
            "# HELP tenant_queue_enqueued_total Total de jobs enfileirados por tenant.",
            "# TYPE tenant_queue_enqueued_total counter",
            f"tenant_queue_enqueued_total {self.tenant_queue_enqueued_total}",
            "# HELP tenant_queue_processed_total Total de jobs processados por tenant.",
            "# TYPE tenant_queue_processed_total counter",
            f"tenant_queue_processed_total {self.tenant_queue_processed_total}",
            "# HELP tenant_queue_failed_total Total de jobs falhos por tenant.",
            "# TYPE tenant_queue_failed_total counter",
            f"tenant_queue_failed_total {self.tenant_queue_failed_total}",
            "# HELP tenant_queue_retried_total Total de jobs reenfileirados por tenant.",
            "# TYPE tenant_queue_retried_total counter",
            f"tenant_queue_retried_total {self.tenant_queue_retried_total}",
            "# HELP tenant_queue_dead_letter_total Total de jobs enviados para DLQ por tenant.",
            "# TYPE tenant_queue_dead_letter_total counter",
            f"tenant_queue_dead_letter_total {self.tenant_queue_dead_letter_total}",
            "# HELP tenant_destination_delivery_total Total de registros entregues em destinos por tenant.",
            "# TYPE tenant_destination_delivery_total counter",
            f"tenant_destination_delivery_total {self.tenant_destination_delivery_total}",
            "# HELP tenant_destination_delivery_failed_total Total de falhas de entrega em destinos por tenant.",
            "# TYPE tenant_destination_delivery_failed_total counter",
            f"tenant_destination_delivery_failed_total {self.tenant_destination_delivery_failed_total}",
            "# HELP sync_last_success_epoch Timestamp epoch do ultimo sync por empresa.",
            "# TYPE sync_last_success_epoch gauge",
        ]
        for empresa_id, epoch in sorted(self.last_sync_epoch_by_empresa.items()):
            lines.append(f'sync_last_success_epoch{{empresa_id="{empresa_id}"}} {epoch}')
        lines.append("# HELP tenant_scheduler_last_success_epoch Timestamp epoch da ultima execucao do scheduler por empresa.")
        lines.append("# TYPE tenant_scheduler_last_success_epoch gauge")
        for empresa_id, epoch in sorted(self.last_tenant_scheduler_epoch_by_empresa.items()):
            lines.append(f'tenant_scheduler_last_success_epoch{{empresa_id="{empresa_id}"}} {epoch}')
        lines.append("# HELP tenant_queue_last_event_epoch Timestamp epoch do ultimo evento da fila por empresa.")
        lines.append("# TYPE tenant_queue_last_event_epoch gauge")
        for empresa_id, epoch in sorted(self.last_tenant_queue_epoch_by_empresa.items()):
            lines.append(f'tenant_queue_last_event_epoch{{empresa_id="{empresa_id}"}} {epoch}')
        lines.append("# HELP tenant_destination_last_event_epoch Timestamp epoch do ultimo evento de destino por empresa.")
        lines.append("# TYPE tenant_destination_last_event_epoch gauge")
        for empresa_id, epoch in sorted(self.last_tenant_destination_epoch_by_empresa.items()):
            lines.append(f'tenant_destination_last_event_epoch{{empresa_id="{empresa_id}"}} {epoch}')
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
