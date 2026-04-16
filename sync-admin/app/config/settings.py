from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'Sync Admin Panel'
    app_env: str = 'development'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    secret_key: str = Field(default='change-me', alias='SECRET_KEY')

    database_url: str = Field(default='sqlite:///./sync_admin.db', alias='DATABASE_URL')

    initial_admin_username: str = Field(default='admin', alias='INITIAL_ADMIN_USERNAME')
    initial_admin_password: str = Field(default='admin123', alias='INITIAL_ADMIN_PASSWORD')

    integration_api_key: str = Field(default='sync-key-change-me', alias='INTEGRATION_API_KEY')
    control_api_base_url: str = Field(default='http://host.docker.internal:8000', alias='CONTROL_API_BASE_URL')
    control_admin_token: str = Field(default='change-this-admin-token', alias='CONTROL_ADMIN_TOKEN')
    control_empresa_id: str = Field(default='12345678000199', alias='CONTROL_EMPRESA_ID')
    control_empresa_nome: str = Field(default='Empresa XD', alias='CONTROL_EMPRESA_NOME')
    agent_api_key_file: str = Field(default='/shared/agent_api_key.txt', alias='AGENT_API_KEY_FILE')
    agent_audit_file: str = Field(default='/shared/agent_audit.log', alias='AGENT_AUDIT_FILE')

    log_level: str = 'INFO'


settings = Settings()
