import uuid

from fastapi import HTTPException, status

from backend.models.empresa import Empresa
from backend.repositories.empresa_repository import EmpresaRepository
from backend.schemas.empresa import EmpresaCreateRequest, EmpresaUpdateRequest
from backend.utils.security import normalize_cnpj, validate_cnpj


class EmpresaService:
    def __init__(self, repository: EmpresaRepository) -> None:
        self.repository = repository

    def list_empresas(self) -> list[Empresa]:
        return self.repository.list_all()

    def get_empresa(self, empresa_id: str) -> Empresa:
        empresa = self.repository.get_by_id(empresa_id)
        if not empresa:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa not found")
        return empresa

    def create_empresa(self, payload: EmpresaCreateRequest) -> Empresa:
        cnpj = normalize_cnpj(payload.cnpj)
        if not validate_cnpj(cnpj):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid CNPJ")
        if self.repository.get_by_cnpj(cnpj):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CNPJ already exists")
        empresa = Empresa(id=str(uuid.uuid4()), cnpj=cnpj, nome=payload.nome.strip())
        return self.repository.add(empresa)

    def update_empresa(self, empresa_id: str, payload: EmpresaUpdateRequest) -> Empresa:
        empresa = self.get_empresa(empresa_id)
        if payload.nome is not None:
            empresa.nome = payload.nome.strip()
        if payload.ativo is not None:
            empresa.ativo = payload.ativo
        return empresa
