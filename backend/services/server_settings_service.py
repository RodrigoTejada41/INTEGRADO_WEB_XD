from backend.config.settings import Settings, get_settings
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.schemas.server_settings import ServerSettingsResponse, ServerSettingsUpdateRequest


class ServerSettingsService:
    DEFAULTS = {
        "ingestion_enabled": "true",
        "max_batch_size": "1000",
        "retention_mode": "archive",
        "retention_months": "14",
    }

    def __init__(self, repository: ServerSettingRepository, app_settings: Settings | None = None):
        self.repository = repository
        self.app_settings = app_settings or get_settings()

    def ensure_defaults(self) -> None:
        current = self.repository.get_many(list(self.DEFAULTS.keys()))
        for key, default_value in self.DEFAULTS.items():
            if key not in current:
                if key == "retention_mode":
                    default_value = self.app_settings.retention_mode
                if key == "retention_months":
                    default_value = str(self.app_settings.retention_months)
                if key == "max_batch_size":
                    default_value = str(self.app_settings.batch_max_size)
                self.repository.upsert(key, str(default_value))

    def get_settings(self) -> ServerSettingsResponse:
        self.ensure_defaults()
        current = self.repository.get_many(list(self.DEFAULTS.keys()))
        return ServerSettingsResponse(
            ingestion_enabled=current.get("ingestion_enabled", "true").lower() == "true",
            max_batch_size=int(current.get("max_batch_size", "1000")),
            retention_mode=current.get("retention_mode", "archive"),
            retention_months=int(current.get("retention_months", "14")),
        )

    def update_settings(self, payload: ServerSettingsUpdateRequest) -> ServerSettingsResponse:
        self.repository.upsert("ingestion_enabled", "true" if payload.ingestion_enabled else "false")
        self.repository.upsert("max_batch_size", str(payload.max_batch_size))
        self.repository.upsert("retention_mode", payload.retention_mode)
        self.repository.upsert("retention_months", str(payload.retention_months))
        return self.get_settings()

