from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.health_api import router as health_router
from app.api.routes.remote_control_api import router as remote_control_router
from app.api.routes.sync_api import router as sync_router
from app.config.settings import settings
from app.core.correlation import bind_request_context
from app.core.db import Base, engine, SessionLocal, ensure_compatible_schema
from app.core.logging import configure_logging
from app.models import (
    AdminUserAuditLog,
    IntegrationKey,
    LocalRuntimeSetting,
    RemoteCommandLog,
    User,
    UserBranchPermission,
)  # noqa: F401
from app.services.auth_service import AuthService
from app.services.local_config_service import LocalConfigService
from app.services.remote_agent_service import RemoteAgentService
from app.services.sync_service import SyncService
from app.web.routes.pages import router as pages_router

configure_logging()

BASE_DIR = Path(__file__).resolve().parent
remote_stop_event: asyncio.Event | None = None
remote_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global remote_stop_event, remote_task
    Base.metadata.create_all(bind=engine)
    ensure_compatible_schema()
    with SessionLocal() as db:
        AuthService(db).ensure_initial_admin(settings.initial_admin_username, settings.initial_admin_password)
        SyncService(db).ensure_default_api_key(settings.integration_api_key)
        LocalConfigService(db).bootstrap()
        LocalConfigService(db).record_state('started_at', datetime.now(UTC).isoformat())
    if settings.remote_command_pull_enabled:
        remote_stop_event = asyncio.Event()
        remote_task = asyncio.create_task(RemoteAgentService.background_loop(SessionLocal, remote_stop_event))
    yield
    if remote_stop_event is not None:
        remote_stop_event.set()
    if remote_task is not None:
        await remote_task


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site='lax', https_only=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def request_observability(request: Request, call_next):
    started = datetime.now(UTC)
    request_id = request.headers.get('X-Request-Id') or f"sync-admin-{int(started.timestamp() * 1000)}"
    correlation_id = request.headers.get('X-Correlation-Id') or request_id
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    with bind_request_context(request_id=request_id, correlation_id=correlation_id):
        response = await call_next(request)

    duration_ms = (datetime.now(UTC) - started).total_seconds() * 1000.0
    response.headers['X-Request-Id'] = request_id
    response.headers['X-Correlation-Id'] = correlation_id
    response.headers['X-Response-Time-ms'] = f'{duration_ms:.3f}'
    return response

app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')

app.include_router(health_router)
app.include_router(remote_control_router)
app.include_router(sync_router)
app.include_router(pages_router)
