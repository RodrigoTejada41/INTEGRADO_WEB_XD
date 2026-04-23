from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import re

import httpx

from agent_local.pairing.env_store import EnvStore


@dataclass(slots=True)
class PairingRequest:
    api_base_url: str
    pairing_code: str
    device_label: str
    empresa_id: str
    api_key_file: str
    env_file: str


@dataclass(slots=True)
class PairingResult:
    empresa_id: str
    api_key_file: str
    env_file: str


@dataclass(slots=True)
class ManualConfigRequest:
    api_base_url: str
    empresa_id: str
    api_key: str
    api_key_file: str
    device_label: str
    env_file: str
    verify_ssl: bool = True


_PAIRING_CODE_LIKE = re.compile(r"^[A-Z0-9]{4}-[A-Z0-9]{4}$")


def normalize_api_base_url(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        raise ValueError("URL da API obrigatoria.")

    if "://" not in value:
        if _PAIRING_CODE_LIKE.fullmatch(value.upper()):
            raise ValueError("Voce informou um codigo de vinculacao no campo da URL da API.")
        value = f"https://{value}"

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL da API invalida. Use http:// ou https://.")

    return value.rstrip("/")


class PairingService:
    def activate(self, request: PairingRequest) -> PairingResult:
        base_url = normalize_api_base_url(request.api_base_url)
        payload = {
            "pairing_code": request.pairing_code.strip(),
            "device_label": request.device_label.strip() or "local-agent",
        }

        try:
            with httpx.Client(timeout=30, verify=True) as client:
                response = client.post(f"{base_url}/agent/pairings/activate", json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_http_error_detail(exc.response)
            raise RuntimeError(f"Falha na vinculacao: {detail}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Falha ao acessar a API: {exc}") from exc

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

        base_url = normalize_api_base_url(request.api_base_url)
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
        base_url = normalize_api_base_url(api_base_url)
        try:
            with httpx.Client(timeout=15, verify=verify_ssl) as client:
                response = client.get(f"{base_url}/health")
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = self._extract_http_error_detail(exc.response)
            raise RuntimeError(f"Falha ao testar a API: {detail}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Falha ao testar a API: {exc}") from exc
        return str(data.get("status", "ok"))

    @staticmethod
    def _extract_http_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text.strip()

        if isinstance(payload, dict):
            detail = payload.get("detail")
            if detail:
                return str(detail)
            return str(payload)

        if payload:
            return str(payload)

        return f"HTTP {response.status_code}"
