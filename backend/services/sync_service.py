from fastapi import HTTPException, status

from backend.repositories.venda_repository import VendaRepository
from backend.schemas.sync import SyncRequest, SyncResponse
from backend.utils.metrics import metrics_registry


class SyncService:
    def __init__(
        self,
        venda_repository: VendaRepository,
        ingestion_enabled: bool = True,
        max_batch_size: int = 1000,
    ):
        self.venda_repository = venda_repository
        self.ingestion_enabled = ingestion_enabled
        self.max_batch_size = max_batch_size

    def sync_batch(self, tenant_empresa_id: str, payload: SyncRequest) -> SyncResponse:
        if not self.ingestion_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ingestion desabilitada por configuracao do servidor.",
            )

        if len(payload.records) > self.max_batch_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lote excede max_batch_size={self.max_batch_size}.",
            )

        if payload.empresa_id != tenant_empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="empresa_id do payload difere da credencial.",
            )

        records = []
        for record in payload.records:
            records.append(
                {
                    "uuid": str(record.uuid),
                    "produto": record.produto,
                    "valor": record.valor,
                    "data": record.data,
                    "data_atualizacao": record.data_atualizacao,
                }
            )

        inserted_count, updated_count = self.venda_repository.bulk_upsert(
            empresa_id=tenant_empresa_id,
            records=records,
        )
        metrics_registry.record_sync_success(
            empresa_id=tenant_empresa_id,
            inserted_count=inserted_count,
            updated_count=updated_count,
        )
        processed_count = inserted_count + updated_count
        return SyncResponse(
            status="ok",
            empresa_id=tenant_empresa_id,
            inserted_count=inserted_count,
            updated_count=updated_count,
            processed_count=processed_count,
        )
