from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from agent_local.pairing.env_store import EnvStore


@dataclass
class PairingRequest:
    api_base_url: str
    pairing_code: str
    device_label: str
    empresa_id: str
    api_key_file: str
    env_file: str


@dataclass
class PairingResult:
    empresa_id: str
    api_key_file: str
    env_file: str


@dataclass
class ManualConfigRequest:
    api_base_url: str
    empresa_id: str
    api_key: str
    api_key_file: str
    device_label: str
    env_file: str
    verify_ssl: bool = True


class PairingService:
    def activate(self, request: PairingRequest) -> PairingResult:
        base_url = request.api_base_url.rstrip("/")
        payload = {
            "pairing_code": request.pairing_code.strip(),
            "device_label": request.device_label.strip() or "local-agent",
        }
        with httpx.Client(timeout=30, verify=True) as client:
            response = client.post(f"{base_url}/agent/pairings/activate", json=payload)
            response.raise_for_status()
            data = response.json()

        activated_empresa_id = str(data["empresa_id"])
        api_key = str(data["api_key"]).strip()
        if not api_key:
            raise RuntimeError("API key vazia retornada na ativacao.")

        if request.empresa_id and request.empresa_id != activated_empresa_id:
            raise RuntimeError("empresa_id informado difere do tenant retornado pelo codigo.")

        key_file_path = Path(request.api_key_file)
        key_file_path.parent.mkdir(parents=True, exist_ok=True)
        key_file_path.write_text(api_key, encoding="utf-8")

        EnvStore(Path(request.env_file)).update_values(
            {
                "AGENT_API_BASE_URL": base_url,
                "AGENT_EMPRESA_ID": activated_empresa_id,
                "AGENT_PAIRING_CODE": "",
                "AGENT_API_KEY": "",
                "AGENT_API_KEY_FILE": request.api_key_file,
                "AGENT_DEVICE_LABEL": request.device_label.strip() or "local-agent",
            }
        )

        return PairingResult(
            empresa_id=activated_empresa_id,
            api_key_file=str(key_file_path),
            env_file=request.env_file,
        )

    def save_manual_config(self, request: ManualConfigRequest) -> PairingResult:
        if not request.empresa_id.strip():
            raise RuntimeError("empresa_id e obrigatorio para configuracao manual.")

        base_url = request.api_base_url.rstrip("/")
        api_key = request.api_key.strip()
        if not api_key:
            raise RuntimeError("API key e obrigatoria para configuracao manual.")

        key_file_path = Path(request.api_key_file)
        key_file_path.parent.mkdir(parents=True, exist_ok=True)
        key_file_path.write_text(api_key, encoding="utf-8")

        EnvStore(Path(request.env_file)).update_values(
            {
                "AGENT_API_BASE_URL": base_url,
                "AGENT_EMPRESA_ID": request.empresa_id.strip(),
                "AGENT_PAIRING_CODE": "",
                "AGENT_API_KEY": "",
                "AGENT_API_KEY_FILE": request.api_key_file,
                "AGENT_DEVICE_LABEL": request.device_label.strip() or "local-agent",
                "VERIFY_SSL": "true" if request.verify_ssl else "false",
            }
        )

        return PairingResult(
            empresa_id=request.empresa_id.strip(),
            api_key_file=str(key_file_path),
            env_file=request.env_file,
        )

    def test_server(self, api_base_url: str, verify_ssl: bool = True) -> str:
        base_url = api_base_url.rstrip("/")
        with httpx.Client(timeout=15, verify=verify_ssl) as client:
            response = client.get(f"{base_url}/health")
            response.raise_for_status()
            data = response.json()
        return str(data.get("status", "ok"))
