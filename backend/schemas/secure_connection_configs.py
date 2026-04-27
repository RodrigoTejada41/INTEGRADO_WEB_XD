from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.tenant_configs import TenantConfigResponse


class SecureConnectionConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str = Field(pattern="^(source|destination)$")
    nome: str = Field(min_length=1, max_length=120)
    connector_type: str = Field(min_length=2, max_length=32)
    sync_interval_minutes: int = Field(default=16, ge=1, le=1440)
    settings: dict[str, str] = Field(default_factory=dict)
    secret_settings: dict[str, str] = Field(default_factory=dict)
    generate_access_key: bool = Field(default=False)
    access_key_field: str | None = Field(default=None, min_length=2, max_length=64)


class SecureConnectionConfigResponse(BaseModel):
    scope: str
    settings_key: str
    secrets_file: str
    generated_access_key: str | None
    config: TenantConfigResponse


class SecureConnectionKeyRotateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_key_field: str | None = Field(default=None, min_length=2, max_length=64)


class SecureConnectionKeyRotateResponse(BaseModel):
    settings_key: str
    secrets_file: str
    access_key_field: str
    generated_access_key: str


class SecureConnectionSecretUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret_settings: dict[str, str] = Field(default_factory=dict)
    merge: bool = Field(default=True)


class SecureConnectionSecretUpdateResponse(BaseModel):
    settings_key: str
    secrets_file: str
    updated_fields: list[str]
