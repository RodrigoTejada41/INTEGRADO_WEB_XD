from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status

from agent_local.tray_app import is_agent_running, restart_agent, start_agent, stop_agent
from agent_local.windows_autostart import find_process_ids


TOKEN_FILE = Path("agent_local/data/local_api_token.txt")

app = FastAPI(title="MoviSync Local Sync API")


def _read_token() -> str | None:
    if not TOKEN_FILE.exists():
        return None
    token = TOKEN_FILE.read_text(encoding="ascii").strip()
    return token or None


def _require_token(x_local_token: str | None = Header(default=None, alias="X-Local-Token")) -> None:
    token = _read_token()
    if not token:
        return
    if x_local_token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local token invalid.",
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status")
def status_view() -> dict[str, object]:
    return {
        "status": "running",
        "sync_running": is_agent_running(),
        "api_pids": find_process_ids("agent_local.local_api"),
        "tray_pids": find_process_ids("agent_local.tray_app"),
        "sync_pids": find_process_ids("agent_local.main"),
    }


@app.post("/sync/start")
def start_sync(_: None = Depends(_require_token)) -> dict[str, str]:
    return {"status": start_agent()}


@app.post("/sync/stop")
def stop_sync(_: None = Depends(_require_token)) -> dict[str, str]:
    return {"status": stop_agent()}


@app.post("/sync/restart")
def restart_sync(_: None = Depends(_require_token)) -> dict[str, str]:
    return {"status": restart_agent()}
