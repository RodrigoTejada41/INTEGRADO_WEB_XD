from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config.database import get_session
from backend.config.memory_database import get_memory_session

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(request: Request) -> dict:
    scheduler_running = bool(getattr(request.app.state, "scheduler_running", False))
    return {
        "status": "ok",
        "components": {
            "api": "ok",
            "scheduler": "running" if scheduler_running else "stopped",
        },
    }


@router.get("/health/live")
def liveness(request: Request) -> dict:
    scheduler_running = bool(getattr(request.app.state, "scheduler_running", False))
    return {
        "status": "live",
        "scheduler_running": scheduler_running,
    }


@router.get("/health/ready")
def readiness(
    request: Request,
    session: Session = Depends(get_session),
    memory_session: Session = Depends(get_memory_session),
) -> dict:
    details: dict[str, str] = {
        "database": "unknown",
        "memory_database": "unknown",
        "scheduler": "unknown",
    }

    try:
        session.execute(text("SELECT 1"))
        details["database"] = "ready"
    except Exception:
        details["database"] = "error"

    try:
        memory_session.execute(text("SELECT 1"))
        details["memory_database"] = "ready"
    except Exception:
        details["memory_database"] = "error"

    scheduler = getattr(request.app.state, "scheduler", None)
    scheduler_running = bool(
        getattr(request.app.state, "scheduler_running", False) or getattr(scheduler, "running", False)
    )
    details["scheduler"] = "ready" if scheduler_running else "starting"

    if any(value in {"error", "starting"} for value in details.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "components": details},
        )

    return {"status": "ready", "components": details}
