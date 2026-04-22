from __future__ import annotations

from fastapi import Request


def build_request_audit_context(request: Request) -> dict[str, str]:
    client_host = str(getattr(request.client, "host", "") or "")
    correlation_id = str(getattr(request.state, "correlation_id", "") or "")
    request_id = str(getattr(request.state, "request_id", "") or "")
    return {
        "correlation_id": correlation_id or request_id,
        "request_path": str(request.url.path),
        "actor_ip": client_host,
        "user_agent": request.headers.get("user-agent", ""),
    }
