import httpx


class SyncApiClient:
    def __init__(
        self,
        base_url: str,
        empresa_id: str,
        api_key: str,
        timeout_seconds: int,
        verify_ssl: bool,
        device_label: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.empresa_id = empresa_id
        self.default_api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl
        self.device_label = (device_label or "agent-local").strip() or "agent-local"

    def send_sync_batch(self, payload: dict, api_key: str | None = None) -> dict:
        current_api_key = api_key or self.default_api_key
        headers = {
            "Content-Type": "application/json",
            "X-Empresa-Id": self.empresa_id,
            "X-API-Key": current_api_key,
        }
        if self.device_label:
            headers["X-Agent-Device-Label"] = self.device_label
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            response = client.post(
                f"{self.base_url}/sync",
                headers=headers,
                json=payload,
            )
        self._raise_for_status(response)
        return response.json()

    def send_sync_status(
        self,
        *,
        last_sync_at: str,
        status: str,
        processed_count: int,
        reason: str,
        api_key: str | None = None,
    ) -> dict:
        current_api_key = api_key or self.default_api_key
        headers = {
            "Content-Type": "application/json",
            "X-Empresa-Id": self.empresa_id,
            "X-API-Key": current_api_key,
            "X-Agent-Device-Label": self.device_label,
        }
        payload = {
            "status": status,
            "last_sync_at": last_sync_at,
            "processed_count": processed_count,
            "reason": reason,
        }
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            response = client.post(
                f"{self.base_url}/sync/status",
                headers=headers,
                json=payload,
            )
        self._raise_for_status(response)
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
        self._raise_for_status(response)
        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text[:2000]
            raise httpx.HTTPStatusError(
                f"{exc} Response body: {body}",
                request=exc.request,
                response=exc.response,
            ) from exc
