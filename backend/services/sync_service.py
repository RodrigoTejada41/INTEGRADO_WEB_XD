from fastapi import HTTPException, status

from backend.repositories.tenant_repository import TenantRepository
from backend.repositories.venda_repository import VendaRepository
from backend.schemas.sync import SyncRequest, SyncResponse
from backend.utils.metrics import metrics_registry


class SyncService:
    def __init__(
        self,
        venda_repository: VendaRepository,
        tenant_repository: TenantRepository | None = None,
        ingestion_enabled: bool = True,
        max_batch_size: int = 1000,
    ):
        self.venda_repository = venda_repository
        self.tenant_repository = tenant_repository
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

        self._apply_source_metadata(tenant_empresa_id, payload)

        records = []
        for record in payload.records:
            records.append(
                {
                    "uuid": str(record.uuid),
                    "branch_code": record.branch_code,
                    "terminal_code": record.terminal_code,
                    "tipo_venda": record.tipo_venda,
                    "forma_pagamento": record.forma_pagamento,
                    "bandeira_cartao": record.bandeira_cartao,
                    "familia_produto": record.familia_produto,
                    "categoria_produto": record.categoria_produto,
                    "codigo_produto_local": record.codigo_produto_local,
                    "unidade": record.unidade,
                    "operador": record.operador,
                    "cliente": record.cliente,
                    "status_venda": record.status_venda,
                    "cancelada": record.cancelada,
                    "produto": record.produto,
                    "quantidade": record.quantidade,
                    "valor_unitario": record.valor_unitario,
                    "valor_bruto": record.valor_bruto,
                    "desconto": record.desconto,
                    "acrescimo": record.acrescimo,
                    "valor_liquido": record.valor_liquido,
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

    def _apply_source_metadata(self, tenant_empresa_id: str, payload: SyncRequest) -> None:
        metadata = payload.source_metadata
        if metadata is None:
            return
        if metadata.cnpj and metadata.cnpj != tenant_empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cnpj da origem difere da credencial.",
            )
        if self.tenant_repository is not None and metadata.company_name:
            self.tenant_repository.update_nome(tenant_empresa_id, metadata.company_name)
