from __future__ import annotations

from fastapi import HTTPException, status

from backend.repositories.produto_de_para_repository import ProdutoDeParaRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.produto_de_para import ProdutoDeParaCreateRequest, ProdutoDeParaUpdateRequest


class ProdutoDeParaService:
    def __init__(
        self,
        tenant_repository: TenantRepository,
        produto_de_para_repository: ProdutoDeParaRepository,
    ):
        self.tenant_repository = tenant_repository
        self.produto_de_para_repository = produto_de_para_repository

    def _ensure_tenant_exists(self, empresa_id: str) -> None:
        if self.tenant_repository.get_by_empresa_id(empresa_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant nao encontrado.")

    @staticmethod
    def _normalize_cnpj(empresa_id: str, cnpj: str | None) -> str:
        normalized = cnpj or empresa_id
        if normalized != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cnpj deve ser igual ao empresa_id do tenant informado.",
            )
        return normalized

    def list(self, *, empresa_id: str, search: str | None = None, limit: int = 100, offset: int = 0):
        self._ensure_tenant_exists(empresa_id)
        return self.produto_de_para_repository.list(
            empresa_id=empresa_id,
            search=search,
            limit=limit,
            offset=offset,
        )

    def create_or_update(self, *, empresa_id: str, payload: ProdutoDeParaCreateRequest):
        self._ensure_tenant_exists(empresa_id)
        values = payload.model_dump()
        values["cnpj"] = self._normalize_cnpj(empresa_id, values.get("cnpj"))
        return self.produto_de_para_repository.upsert_by_local_code(
            empresa_id=empresa_id,
            values=values,
        )

    def update(self, *, empresa_id: str, mapping_id: int, payload: ProdutoDeParaUpdateRequest):
        self._ensure_tenant_exists(empresa_id)
        mapping = self.produto_de_para_repository.get_by_id(empresa_id=empresa_id, mapping_id=mapping_id)
        if mapping is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DE/PARA nao encontrado.")
        values = payload.model_dump(exclude_unset=True)
        if "cnpj" in values:
            values["cnpj"] = self._normalize_cnpj(empresa_id, values.get("cnpj"))
        return self.produto_de_para_repository.update(mapping, values)

    def delete(self, *, empresa_id: str, mapping_id: int) -> None:
        self._ensure_tenant_exists(empresa_id)
        mapping = self.produto_de_para_repository.get_by_id(empresa_id=empresa_id, mapping_id=mapping_id)
        if mapping is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DE/PARA nao encontrado.")
        self.produto_de_para_repository.delete(mapping)

    def list_unmapped_products(self, *, empresa_id: str, limit: int = 100) -> list[dict[str, object]]:
        self._ensure_tenant_exists(empresa_id)
        return self.produto_de_para_repository.list_unmapped_products(empresa_id=empresa_id, limit=limit)
