from pydantic import BaseModel, ConfigDict, Field


class ServerSettingsResponse(BaseModel):
    ingestion_enabled: bool
    max_batch_size: int
    retention_mode: str
    retention_months: int
    connection_secrets_file: str


class ServerSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion_enabled: bool = Field(default=True)
    max_batch_size: int = Field(default=1000, ge=1, le=10000)
    retention_mode: str = Field(default="archive")
    retention_months: int = Field(default=14, ge=1, le=120)
    connection_secrets_file: str = Field(
        default="output/tenant_connection_secrets.json",
        min_length=1,
        max_length=255,
    )
