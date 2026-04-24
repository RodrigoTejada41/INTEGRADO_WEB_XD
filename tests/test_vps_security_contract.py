from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deploy_user_script_enforces_restricted_ssh_access() -> None:
    script = (ROOT / "infra" / "scripts" / "setup-deploy-user.sh").read_text(encoding="utf-8")

    assert "DEPLOY_PUBLIC_KEY" in script
    assert "DEPLOY_FROM" in script
    assert "no-agent-forwarding" in script
    assert "no-port-forwarding" in script
    assert "no-pty" in script
    assert "no-user-rc" in script
    assert "no-X11-forwarding" in script
    assert 'command=\\"/usr/bin/env APP_DIR=${APP_DIR} bash ${APP_DIR}/infra/scripts/update.sh\\"' in script
    assert "sudo usermod -aG docker" in script
    assert "sudo install -d -m 700" in script
    assert "authorized_keys" in script


def test_production_workflow_uses_secret_driven_deploy_access() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy-prod.yml").read_text(encoding="utf-8")

    assert "VPS_HOST" in workflow
    assert "VPS_USER" in workflow
    assert "VPS_SSH_KEY" in workflow
    assert "VPS_PORT" in workflow
    assert "infra/scripts/update.sh" in workflow
    assert "curl -fsS \"http://${{ secrets.VPS_HOST }}/healthz\"" in workflow
    assert "curl -fsS \"http://${{ secrets.VPS_HOST }}/readyz/backend\"" in workflow
    assert "curl -fsS \"http://${{ secrets.VPS_HOST }}/readyz/sync-admin\"" in workflow
