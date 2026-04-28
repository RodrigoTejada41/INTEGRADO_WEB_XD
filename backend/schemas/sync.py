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
    familia_produto: str | None = Field(default=None, max_length=160)
    produto: str = Field(min_length=1, max_length=255)
    valor: Decimal = Field(gt=Decimal("0"))
    data: date
    data_atualizacao: datetime

    @field_validator("data_atualizacao")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    empresa_id: str = Field(min_length=3, max_length=32)
    records: list[VendaPayload] = Field(min_length=1)


class SyncResponse(BaseModel):
    status: str
    empresa_id: str
    inserted_count: int
    updated_count: int
    processed_count: int
