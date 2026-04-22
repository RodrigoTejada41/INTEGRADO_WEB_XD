from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_production_compose_uses_sync_admin_readiness() -> None:
    compose_content = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "integrado_backend" in compose_content
    assert "integrado_frontend" in compose_content
    assert "integrado_nginx" in compose_content
    assert "healthcheck" in compose_content
    assert "http://localhost:8000/health" in compose_content
    assert "http://localhost:8000/health/ready" not in compose_content


def test_dev_workflow_targets_dedicated_dev_vps() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy-dev.yml").read_text(encoding="utf-8")

    assert "Deploy Dev VPS" in workflow
    assert "DEV_VPS_HOST" in workflow
    assert "DEV_VPS_USER" in workflow
    assert "DEV_VPS_SSH_KEY" in workflow
    assert "DEV_VPS_APP_DIR" in workflow
    assert "DEV_VPS_BRANCH" in workflow
    assert "/opt/integrado_web_xd-dev" in workflow
    assert "BRANCH=\"${{ secrets.DEV_VPS_BRANCH || 'dev' }}\"" in workflow
    assert "Missing required DEV_VPS_* secrets" in workflow
    assert 'git reset --hard "origin/$BRANCH"' in workflow


def test_deploy_script_waits_for_runtime_health_before_edge_checks() -> None:
    deploy_script = (ROOT / "infra" / "scripts" / "deploy-prod.sh").read_text(encoding="utf-8")

    assert "docker compose" in deploy_script
    assert "up -d --build --remove-orphans" in deploy_script
    assert "sleep 10" in deploy_script
    assert "curl -fsS http://127.0.0.1/healthz" in deploy_script
    assert "curl -fsS http://127.0.0.1/api/health" in deploy_script


def test_deploy_workflow_guards_optional_scripts_and_checks_edge_readiness_chain() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy-prod.yml").read_text(encoding="utf-8")

    assert "Deploy Production VPS" in workflow
    assert "VPS_HOST" in workflow
    assert "VPS_USER" in workflow
    assert "VPS_SSH_KEY" in workflow
    assert "curl -fsS \"http://${{ secrets.VPS_HOST }}/healthz\"" in workflow
    assert "curl -fsS \"http://${{ secrets.VPS_HOST }}/healthz\"" in workflow


def test_nginx_exposes_explicit_backend_and_sync_admin_readiness_routes() -> None:
    nginx_config = (ROOT / "infra" / "nginx" / "default.conf").read_text(encoding="utf-8")

    assert "upstream frontend_app" in nginx_config
    assert "upstream backend_api" in nginx_config
    assert "location /healthz" in nginx_config
    assert "location /api/" in nginx_config
    assert "proxy_pass http://backend_api/;" in nginx_config
