from __future__ import annotations

from pathlib import Path

import pytest

from agent_local.pairing.service import (
    ManualConfigRequest,
    PairingService,
    normalize_api_base_url,
)


def test_save_manual_config_writes_key_and_env(tmp_path: Path) -> None:
    base_dir = tmp_path / "test_agent_pairing_service"
    base_dir.mkdir(parents=True, exist_ok=True)

    env_file = base_dir / ".env"
    key_file = base_dir / "agent_api_key.txt"
    service = PairingService()

    result = service.save_manual_config(
        ManualConfigRequest(
            api_base_url="https://movisystecnologia.com.br/admin/api",
            empresa_id="12345678000199",
            api_key="key-abc-123",
            api_key_file=str(key_file),
            device_label="loja-01",
            env_file=str(env_file),
            verify_ssl=True,
        )
    )

    assert result.empresa_id == "12345678000199"
    assert key_file.exists()
    assert key_file.read_text(encoding="utf-8") == "key-abc-123"

    env_text = env_file.read_text(encoding="utf-8")
    assert "AGENT_API_BASE_URL=https://movisystecnologia.com.br/admin/api" in env_text
    assert "AGENT_EMPRESA_ID=12345678000199" in env_text
    assert f"AGENT_API_KEY_FILE={key_file}" in env_text
    assert "AGENT_DEVICE_LABEL=loja-01" in env_text


def test_normalize_api_base_url_rejects_pairing_code() -> None:
    with pytest.raises(ValueError, match="codigo de vinculacao"):
        normalize_api_base_url("FPJ9-FSHZ")
