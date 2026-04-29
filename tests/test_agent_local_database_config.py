from pathlib import Path

from agent_local.config.database_config import (
    LocalDatabaseConfig,
    LocalDatabaseConfigService,
    build_mariadb_url,
    parse_mariadb_url,
)


def test_build_mariadb_url_keeps_real_password_and_escapes_special_chars() -> None:
    config = LocalDatabaseConfig(
        database_type="mariadb",
        host="192.168.0.10",
        port=3306,
        database="xd",
        username="user",
        password="p@ss:word/123",
    )

    url = build_mariadb_url(config)

    assert url.startswith("mysql+pymysql://user:")
    assert "***" not in url
    assert "192.168.0.10:3306/xd" in url
    parsed = parse_mariadb_url(url)
    assert parsed.password == "p@ss:word/123"


def test_save_local_database_config_updates_env_without_json_manual() -> None:
    output_dir = Path("output/test_agent_local_database_config")
    output_dir.mkdir(parents=True, exist_ok=True)
    env_file = output_dir / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AGENT_API_BASE_URL=https://movisystecnologia.com.br/admin/api",
                "AGENT_EMPRESA_ID=12345678000199",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    service = LocalDatabaseConfigService()
    result = service.save_config(
        env_file=str(env_file),
        config=LocalDatabaseConfig(
            database_type="mariadb",
            host="127.0.0.1",
            port=3308,
            database="xd",
            username="root",
            password="root",
            sync_interval_minutes=16,
            batch_size=750,
        ),
    )

    env_text = env_file.read_text(encoding="utf-8")
    assert "AGENT_MARIADB_URL=mysql+pymysql://root:root@127.0.0.1:3308/xd?charset=utf8mb4" in env_text
    assert "AGENT_SOURCE_QUERY=auto" in env_text
    assert "SYNC_INTERVAL_MINUTES=16" in env_text
    assert "BATCH_SIZE=750" in env_text
    assert result.host == "127.0.0.1"
    assert result.database == "xd"
