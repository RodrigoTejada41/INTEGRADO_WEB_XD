import httpx

from agent_local.db.mariadb_client import MariaDBClient


class AgentHealthcheck:
    def __init__(
        self,
        mariadb_client: MariaDBClient,
        api_base_url: str,
        timeout_seconds: int,
        verify_ssl: bool,
    ):
        self.mariadb_client = mariadb_client
        self.api_base_url = api_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl

    def check_mariadb(self) -> bool:
        return self.mariadb_client.ping()

    def check_api(self) -> bool:
        with httpx.Client(timeout=self.timeout_seconds, verify=self.verify_ssl) as client:
            response = client.get(f"{self.api_base_url}/health")
        response.raise_for_status()
        return True

    def run_preflight(self) -> dict:
        maria_ok = False
        api_ok = False
        errors: list[str] = []

        try:
            maria_ok = self.check_mariadb()
        except Exception as exc:
            errors.append(f"mariadb: {exc}")

        try:
            api_ok = self.check_api()
        except Exception as exc:
            errors.append(f"api: {exc}")

        return {
            "ok": maria_ok and api_ok,
            "mariadb_ok": maria_ok,
            "api_ok": api_ok,
            "errors": errors,
        }

