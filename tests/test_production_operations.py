from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_production_compose_uses_sync_admin_readiness() -> None:
    compose_content = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "http://localhost:8000/health/ready" in compose_content
    assert "http://localhost:8000/health/live" not in compose_content
    assert "http://127.0.0.1/readyz/backend" in compose_content
    assert "http://127.0.0.1/readyz/sync-admin" in compose_content


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


def test_deploy_script_waits_for_runtime_health_before_edge_checks() -> None:
    deploy_script = (ROOT / "infra" / "scripts" / "deploy-prod.sh").read_text(encoding="utf-8")

    assert "wait_for_container_health" in deploy_script
    assert 'wait_for_container_health "integrado-backend"' in deploy_script
    assert 'wait_for_container_health "integrado-frontend"' in deploy_script
    assert 'wait_for_container_health "integrado-nginx"' in deploy_script
    assert "http://127.0.0.1/api/health/ready" in deploy_script
    assert "http://127.0.0.1/readyz/backend" in deploy_script
    assert "http://127.0.0.1/readyz/sync-admin" in deploy_script


def test_deploy_workflow_guards_optional_scripts_and_checks_edge_readiness_chain() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy-prod.yml").read_text(encoding="utf-8")

    assert 'if [ -f "infra/scripts/install-monitoring-cron.sh" ]; then' in workflow
    assert 'if [ -f "infra/scripts/install-backup-cron.sh" ]; then' in workflow
    assert 'if [ -f "infra/scripts/enable-https.sh" ]; then' in workflow
    assert 'if [ -f "infra/scripts/install-https-cron.sh" ]; then' in workflow
    assert 'curl -fsS "http://${{ secrets.VPS_HOST }}/api/health/ready"' in workflow
    assert 'curl -fsS "http://${{ secrets.VPS_HOST }}/readyz/backend"' in workflow
    assert 'curl -fsS "http://${{ secrets.VPS_HOST }}/readyz/sync-admin"' in workflow


def test_nginx_exposes_explicit_backend_and_sync_admin_readiness_routes() -> None:
    nginx_config = (ROOT / "infra" / "nginx" / "default.conf").read_text(encoding="utf-8")

    assert "location = /readyz/backend" in nginx_config
    assert "proxy_pass http://backend_upstream/health/ready;" in nginx_config
    assert "location = /readyz/sync-admin" in nginx_config
    assert "proxy_pass http://frontend_upstream/health/ready;" in nginx_config
