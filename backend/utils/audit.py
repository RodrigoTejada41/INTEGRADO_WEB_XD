from __future__ import annotations

from fastapi import Request


def build_request_audit_context(request: Request) -> dict[str, str]:
    client_host = request.client.host if request.client else ""
    return {
        "correlation_id": str(getattr(request.state, "correlation_id", "") or ""),
        "request_path": request.url.path,
        "actor_ip": client_host,
        "user_agent": request.headers.get("User-Agent", "")[:255],
    }
