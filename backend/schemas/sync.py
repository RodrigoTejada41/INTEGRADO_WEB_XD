from datetime import UTC, date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class VendaPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uuid: str = Field(min_length=8, max_length=128)
    branch_code: str | None = Field(default=None, max_length=50)
    terminal_code: str | None = Field(default=None, max_length=50)
    tipo_venda: str | None = Field(default=None, max_length=80)
    forma_pagamento: str | None = Field(default=None, max_length=120)
    bandeira_cartao: str | None = Field(default=None, max_length=80)
    familia_produto: str | None = Field(default=None, max_length=160)
    categoria_produto: str | None = Field(default=None, max_length=160)
    codigo_produto_local: str | None = Field(default=None, max_length=120)
    unidade: str | None = Field(default=None, max_length=30)
    operador: str | None = Field(default=None, max_length=120)
    cliente: str | None = Field(default=None, max_length=160)
    status_venda: str | None = Field(default=None, max_length=80)
    cancelada: bool = False
    produto: str = Field(min_length=1, max_length=255)
    quantidade: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    valor_unitario: Decimal | None = Field(default=None, ge=Decimal("0"))
    valor_bruto: Decimal | None = Field(default=None, ge=Decimal("0"))
    desconto: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    acrescimo: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    valor_liquido: Decimal | None = Field(default=None, ge=Decimal("0"))
    valor: Decimal = Field(gt=Decimal("0"))
    data: date
    data_atualizacao: datetime

    @field_validator("data_atualizacao")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class SyncSourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cnpj: str | None = Field(default=None, min_length=3, max_length=32)
    company_name: str | None = Field(default=None, min_length=1, max_length=120)
    payment_methods: list[str] = Field(default_factory=list, max_length=100)


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresa_id: str = Field(min_length=3, max_length=32)
    source_metadata: SyncSourceMetadata | None = None
    records: list[VendaPayload] = Field(min_length=1)


class SyncResponse(BaseModel):
    status: str
    empresa_id: str
    inserted_count: int
    updated_count: int
    processed_count: int


class SyncStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="success", max_length=24)
    last_sync_at: datetime
    processed_count: int = Field(default=0, ge=0)
    reason: str | None = Field(default=None, max_length=120)


class SyncStatusResponse(BaseModel):
    status: str
    empresa_id: str
    client_id: str
    last_sync_at: datetime
