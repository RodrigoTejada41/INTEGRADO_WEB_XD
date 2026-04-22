import httpx


class SyncApiClient:
    def __init__(
        self,
        base_url: str,
        empresa_id: str,
        api_key: str,
        timeout_seconds: int,
        verify_ssl: bool,
    ):
        self.base_url = base_url.rstrip("/")
        self.empresa_id = empresa_id
        self.default_api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl

    def send_sync_batch(self, payload: dict, api_key: str | None = None) -> dict:
        current_api_key = api_key or self.default_api_key
        headers = {
            "Content-Type": "application/json",
            "X-Empresa-Id": self.empresa_id,
            "X-API-Key": current_api_key,
        }
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            response = client.post(
                f"{self.base_url}/sync",
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        return response.json()

    def activate_pairing_code(self, pairing_code: str, device_label: str) -> dict:
        payload = {
            "pairing_code": pairing_code,
            "device_label": device_label,
        }
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            response = client.post(
                f"{self.base_url}/agent/pairings/activate",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        return response.json()
