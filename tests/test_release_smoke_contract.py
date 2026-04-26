from __future__ import annotations

import os

import httpx
import pytest


def _get_release_smoke_base_url() -> str:
    base_url = os.getenv("RELEASE_SMOKE_BASE_URL", "").strip()
    if not base_url:
        pytest.skip("RELEASE_SMOKE_BASE_URL nao informado.")
    return base_url.rstrip("/")


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def test_release_smoke_validates_public_edge_and_readiness() -> None:
    base_url = _get_release_smoke_base_url()
    verify_ssl = _is_truthy(os.getenv("RELEASE_SMOKE_VERIFY_SSL", "true"))
    timeout = float(os.getenv("RELEASE_SMOKE_TIMEOUT_SECONDS", "15"))

    with httpx.Client(base_url=base_url, timeout=timeout, verify=verify_ssl, follow_redirects=True) as client:
        healthz = client.get("/healthz")
        assert healthz.status_code == 200, healthz.text
        assert healthz.text.strip() == "ok"

        backend_ready = client.get("/readyz/backend")
        assert backend_ready.status_code == 200, backend_ready.text
        assert backend_ready.json()["status"] == "ready"
        assert backend_ready.json()["components"]["database"] == "ready"

        sync_admin_ready = client.get("/readyz/sync-admin")
        assert sync_admin_ready.status_code == 200, sync_admin_ready.text
        assert sync_admin_ready.json()["status"] == "ready"
        assert sync_admin_ready.json()["components"]["control_api"] == "ready"

        backend_api_ready = client.get("/admin/api/health/ready")
        assert backend_api_ready.status_code == 200, backend_api_ready.text
        assert backend_api_ready.json()["status"] == "ready"

        admin_edge = client.get("/admin/")
        assert admin_edge.status_code in {200, 302}, admin_edge.text

        client_edge = client.get("/MoviRelatorios/")
        assert client_edge.status_code in {200, 302}, client_edge.text

