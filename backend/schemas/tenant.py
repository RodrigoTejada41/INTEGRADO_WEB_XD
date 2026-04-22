from pydantic import BaseModel, ConfigDict, Field


class TenantProvisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresa_id: str = Field(min_length=3, max_length=32)
    nome: str = Field(min_length=1, max_length=120)


class TenantProvisionResponse(BaseModel):
    empresa_id: str
    nome: str
    api_key: str
    status: str


class TenantRotateKeyResponse(BaseModel):
    empresa_id: str
    api_key: str
    status: str


class TenantListItemResponse(BaseModel):
    empresa_id: str
    nome: str
    ativo: bool


class TenantDeactivateResponse(BaseModel):
    empresa_id: str
    status: str

