from pydantic import BaseModel, Field


class EmpresaCreateRequest(BaseModel):
    cnpj: str = Field(min_length=14, max_length=18)
    nome: str = Field(min_length=2, max_length=150)


class EmpresaUpdateRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    ativo: bool | None = None


class EmpresaResponse(BaseModel):
    id: str
    cnpj: str
    nome: str
    ativo: bool
