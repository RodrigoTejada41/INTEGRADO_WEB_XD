import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from backend.api.routes import (
    health_router,
    metrics_router,
    sync_router,
    tenant_admin_router,
    tenant_pairing_router,
)
from backend.config.database import SessionLocal, engine
from backend.config.logging import configure_logging
from backend.config.settings import get_settings
from backend.models import Base
from backend.services.retention_service import RetentionService
from backend.services.tenant_sync_worker import TenantSyncWorker
from backend.services.tenant_sync_scheduler import TenantSyncScheduler

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)
scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler

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
    tenant_worker = TenantSyncWorker(session_factory=SessionLocal)
    scheduler.add_job(
        tenant_worker.drain_pending_jobs,
        trigger="interval",
        minutes=1,
        id="tenant-sync-worker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("tenant_sync_scheduler_started")

    yield

    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("tenant_sync_scheduler_stopped")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(sync_router)
app.include_router(tenant_admin_router)
app.include_router(tenant_pairing_router)
