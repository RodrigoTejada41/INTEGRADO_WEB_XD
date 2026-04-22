from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantPairingCodeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ttl_minutes: int = Field(default=10, ge=1, le=60)


class TenantPairingCodeCreateResponse(BaseModel):
    empresa_id: str
    pairing_code: str
    expires_at: datetime
    status: str


class TenantPairingActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pairing_code: str = Field(min_length=6, max_length=32)
    device_label: str = Field(default="local-agent", min_length=1, max_length=120)


class TenantPairingActivateResponse(BaseModel):
    empresa_id: str
    api_key: str
    status: str
