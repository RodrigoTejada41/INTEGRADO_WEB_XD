from pydantic import BaseModel


class TenantObservabilityResponse(BaseModel):
    empresa_id: str
    sync_batches_total: int
    sync_failures_total: int
    tenant_scheduler_runs_total: int
    tenant_queue_processed_total: int
    tenant_queue_failed_total: int
    tenant_queue_retried_total: int
    tenant_queue_dead_letter_total: int
    tenant_destination_delivery_total: int
    tenant_destination_delivery_failed_total: int
    sync_last_success_epoch: int
    tenant_scheduler_last_success_epoch: int
    tenant_queue_last_event_epoch: int
    tenant_destination_last_event_epoch: int
    sync_last_success_lag_seconds: int
    tenant_scheduler_last_success_lag_seconds: int
    tenant_queue_last_event_lag_seconds: int
    tenant_destination_last_event_lag_seconds: int
