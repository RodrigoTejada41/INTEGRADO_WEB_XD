import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.api.routes import (
    health_router,
    memory_router,
    metrics_router,
    remote_clients_router,
    sync_router,
    tenant_admin_router,
    tenant_pairing_router,
)
from backend.config.database import SessionLocal, engine
from backend.config.memory_database import init_memory_schema
from backend.config.logging import configure_logging
from backend.config.settings import get_settings
from backend.models import Base
from backend.services.retention_service import RetentionService
from backend.services.tenant_sync_scheduler import TenantSyncScheduler
from backend.services.tenant_sync_worker import TenantSyncWorker
from backend.utils.correlation import bind_correlation_id, bind_log_context
from backend.utils.metrics import metrics_registry
from backend.utils.rate_limit import InMemoryRateLimiter, rate_limit_key

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
scheduler: AsyncIOScheduler | None = None
rate_limiter = InMemoryRateLimiter(settings.rate_limit_requests_per_minute)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    app.state.scheduler_running = False

    init_memory_schema()

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    scheduler = AsyncIOScheduler(timezone="UTC")

    if settings.retention_job_enabled:
        retention_service = RetentionService(
            session_factory=SessionLocal,
            retention_months=settings.retention_months,
            retention_mode=settings.retention_mode,
        )
        scheduler.add_job(
            retention_service.run,
            trigger="interval",
            minutes=settings.retention_job_interval_minutes,
            id="retention-job",
            replace_existing=True,
        )
        logger.info("retention_scheduler_started")

    tenant_scheduler = TenantSyncScheduler(session_factory=SessionLocal, scheduler=scheduler)
    tenant_scheduler.sync_all_jobs()
    scheduler.add_job(
        tenant_scheduler.sync_all_jobs,
        trigger="interval",
        minutes=5,
        id="tenant-sync-reconciler",
        replace_existing=True,
    )
    tenant_worker = TenantSyncWorker(
        session_factory=SessionLocal,
        max_workers=settings.tenant_worker_max_workers,
        chunk_size=settings.sync_ingest_chunk_size,
        max_jobs_per_tenant=settings.tenant_worker_max_jobs_per_tenant,
    )
    scheduler.add_job(
        tenant_worker.drain_pending_jobs,
        trigger="interval",
        minutes=1,
        id="tenant-sync-worker",
        replace_existing=True,
    )
    scheduler.start()
    app.state.scheduler_running = True
    app.state.scheduler = scheduler
    logger.info("tenant_sync_scheduler_started")

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
        app.state.scheduler_running = False
        logger.info("tenant_sync_scheduler_stopped")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.environment.lower() == "production",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(',') if origin.strip()],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def request_observability(request: Request, call_next):
    started = datetime.now(UTC)
    client_host = request.client.host if request.client else 'unknown'
    request_key = rate_limit_key(request.method, request.url.path, client_host)
    request_id = request.headers.get('X-Request-Id') or f"req-{int(started.timestamp() * 1000)}"
    correlation_id = request.headers.get("X-Correlation-Id") or request_id
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id

    with bind_correlation_id(correlation_id), bind_log_context(
        request_id=request_id,
        correlation_id=correlation_id,
        http_method=request.method,
        path=request.url.path,
    ):
        if settings.rate_limit_enabled:
            decision = rate_limiter.allow(request_key)
            if not decision.allowed:
                metrics_registry.record_http_request(
                    method=request.method,
                    path=request.url.path,
                    status_code=429,
                    duration_ms=0.0,
                )
                response = JSONResponse(
                    status_code=429,
                    content={'detail': 'Rate limit excedido.'},
                    headers={'Retry-After': str(decision.retry_after_seconds)},
                )
                response.headers['X-Request-Id'] = request_id
                response.headers['X-Correlation-Id'] = correlation_id
                response.headers['X-Response-Time-ms'] = "0.000"
                return response

        response = await call_next(request)
        duration_ms = (datetime.now(UTC) - started).total_seconds() * 1000.0
        response.headers['X-Request-Id'] = request_id
        response.headers['X-Correlation-Id'] = correlation_id
        response.headers['X-Response-Time-ms'] = f'{duration_ms:.3f}'
        metrics_registry.record_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


app.include_router(health_router)
app.include_router(memory_router)
app.include_router(metrics_router)
app.include_router(remote_clients_router)
app.include_router(sync_router)
app.include_router(tenant_admin_router)
app.include_router(tenant_pairing_router)
