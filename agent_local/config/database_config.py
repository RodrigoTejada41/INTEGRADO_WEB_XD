from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import URL, make_url

from agent_local.db.mariadb_client import MariaDBClient
from agent_local.pairing.env_store import EnvStore


DEFAULT_MARIADB_PORT = 3306
DEFAULT_DATABASE_TYPE = "mariadb"


@dataclass(frozen=True)
class LocalDatabaseConfig:
    database_type: str
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_enabled: bool = False
    source_query: str | None = None
    sync_interval_minutes: int = 15
    batch_size: int = 500


@dataclass(frozen=True)
class LocalDatabaseConfigResult:
    database_url: str
    env_file: str
    database_type: str
    host: str
    port: int
    database: str
    username: str
    ssl_enabled: bool


def build_mariadb_url(config: LocalDatabaseConfig) -> str:
    if config.database_type.lower().strip() != DEFAULT_DATABASE_TYPE:
        raise RuntimeError("Somente MariaDB esta habilitado no agente local atual.")
    if not config.host.strip():
        raise RuntimeError("Host do banco e obrigatorio.")
    if not config.database.strip():
        raise RuntimeError("Nome do banco e obrigatorio.")
    if not config.username.strip():
        raise RuntimeError("Usuario do banco e obrigatorio.")
    if config.port < 1 or config.port > 65535:
        raise RuntimeError("Porta do banco invalida.")

    query = {"charset": "utf8mb4"}
    if config.ssl_enabled:
        query["ssl_disabled"] = "false"

    url = URL.create(
        "mysql+pymysql",
        username=config.username.strip(),
        password=config.password,
        host=config.host.strip(),
        port=config.port,
        database=config.database.strip(),
        query=query,
    )
    return url.render_as_string(hide_password=False)


def parse_mariadb_url(database_url: str) -> LocalDatabaseConfig:
    url = make_url(database_url)
    ssl_enabled = str(url.query.get("ssl_disabled", "true")).lower() == "false"
    return LocalDatabaseConfig(
        database_type=DEFAULT_DATABASE_TYPE,
        host=url.host or "",
        port=int(url.port or DEFAULT_MARIADB_PORT),
        database=url.database or "",
        username=url.username or "",
        password=url.password or "",
        ssl_enabled=ssl_enabled,
    )


class LocalDatabaseConfigService:
    def test_connection(self, config: LocalDatabaseConfig) -> bool:
        database_url = build_mariadb_url(config)
        return MariaDBClient(database_url, source_query=config.source_query).ping()

    def save_config(self, *, config: LocalDatabaseConfig, env_file: str) -> LocalDatabaseConfigResult:
        database_url = build_mariadb_url(config)
        updates = {
            "AGENT_MARIADB_URL": database_url,
            "SYNC_INTERVAL_MINUTES": str(config.sync_interval_minutes),
            "BATCH_SIZE": str(config.batch_size),
        }
        if config.source_query is not None:
            updates["AGENT_SOURCE_QUERY"] = config.source_query

        EnvStore(Path(env_file)).update_values(updates)
        return LocalDatabaseConfigResult(
            database_url=database_url,
            env_file=env_file,
            database_type=config.database_type,
            host=config.host.strip(),
            port=config.port,
            database=config.database.strip(),
            username=config.username.strip(),
            ssl_enabled=config.ssl_enabled,
        )
