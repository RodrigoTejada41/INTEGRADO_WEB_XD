from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProdutoDeParaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: str | None = Field(default=None, max_length=32)
    codigo_produto_local: str = Field(min_length=1, max_length=120)
    codigo_produto_web: str | None = Field(default=None, max_length=120)
    descricao_produto_local: str | None = Field(default=None, max_length=255)
    descricao_produto_web: str | None = Field(default=None, max_length=255)
    familia_local: str | None = Field(default=None, max_length=160)
    familia_web: str | None = Field(default=None, max_length=160)
    categoria_local: str | None = Field(default=None, max_length=160)
    categoria_web: str | None = Field(default=None, max_length=160)
    ativo: bool = True

    @field_validator("*", mode="before")
    @classmethod
    def strip_blank_strings(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ProdutoDeParaUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: str | None = Field(default=None, max_length=32)
    codigo_produto_web: str | None = Field(default=None, max_length=120)
    descricao_produto_local: str | None = Field(default=None, max_length=255)
    descricao_produto_web: str | None = Field(default=None, max_length=255)
    familia_local: str | None = Field(default=None, max_length=160)
    familia_web: str | None = Field(default=None, max_length=160)
    categoria_local: str | None = Field(default=None, max_length=160)
    categoria_web: str | None = Field(default=None, max_length=160)
    ativo: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def strip_blank_strings(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ProdutoDeParaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: str
    cnpj: str
    codigo_produto_local: str
    codigo_produto_web: str | None = None
    descricao_produto_local: str | None = None
    descricao_produto_web: str | None = None
    familia_local: str | None = None
    familia_web: str | None = None
    categoria_local: str | None = None
    categoria_web: str | None = None
    ativo: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProdutoDeParaListResponse(BaseModel):
    empresa_id: str
    items: list[ProdutoDeParaResponse]


class ProdutoSemDeParaResponse(BaseModel):
    codigo_produto_local: str
    descricao_produto_local: str | None = None
    familia_local: str | None = None
    categoria_local: str | None = None
    vendas_count: int


class ProdutoSemDeParaListResponse(BaseModel):
    empresa_id: str
    items: list[ProdutoSemDeParaResponse]


class ProdutoDeParaDeleteResponse(BaseModel):
    empresa_id: str
    id: int
    deleted: bool
