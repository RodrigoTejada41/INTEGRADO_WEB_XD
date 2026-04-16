from __future__ import annotations

import importlib.util
import os
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
API_FILE = ROOT / "apps" / "api-service" / "src" / "main.py"


def _load_app_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, API_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load API module")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@contextmanager
def _client_context(module_name: str = "api_main_test"):
    os.environ["DB_PATH"] = str(ROOT / "output" / f"test_system_{module_name}.db")
    os.environ["AUTH_USERS"] = "admin:admin123:admin;viewer:viewer123:viewer"
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["JWT_ACCESS_EXPIRES_MINUTES"] = "60"
    os.environ["JWT_REFRESH_EXPIRES_MINUTES"] = "120"

    db_file = Path(os.environ["DB_PATH"])
    db_file.parent.mkdir(parents=True, exist_ok=True)
    if db_file.exists():
        db_file.unlink()

    mod = _load_app_module(module_name)
    with TestClient(mod.app) as client:
        yield client


def _login(client: TestClient, username: str, password: str) -> dict:
    r = client.post("/auth/token", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def test_health_and_login_and_me() -> None:
    with _client_context("api_main_test_1") as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        tokens = _login(client, "admin", "admin123")
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["username"] == "admin"


def test_rbac_viewer_cannot_read_files() -> None:
    with _client_context("api_main_test_2") as client:
        tokens = _login(client, "viewer", "viewer123")

        forbidden = client.get(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert forbidden.status_code == 403


def test_refresh_rotation_and_logout_revokes_access() -> None:
    with _client_context("api_main_test_3") as client:
        tokens = _login(client, "admin", "admin123")

        refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert refreshed.status_code == 200, refreshed.text
        refreshed_body = refreshed.json()

        old_refresh_reuse = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert old_refresh_reuse.status_code == 401

        logout = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {refreshed_body['access_token']}"},
            json={"refresh_token": refreshed_body["refresh_token"]},
        )
        assert logout.status_code == 200

        revoked_access = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refreshed_body['access_token']}"},
        )
        assert revoked_access.status_code == 401
