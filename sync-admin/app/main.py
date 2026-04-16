from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.health_api import router as health_router
from app.api.routes.sync_api import router as sync_router
from app.config.settings import settings
from app.core.db import Base, engine, SessionLocal
from app.core.logging import configure_logging
from app.models import IntegrationKey, User  # noqa: F401
from app.services.auth_service import AuthService
from app.services.sync_service import SyncService
from app.web.routes.pages import router as pages_router

configure_logging()

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        AuthService(db).ensure_initial_admin(settings.initial_admin_username, settings.initial_admin_password)
        SyncService(db).ensure_default_api_key(settings.integration_api_key)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site='lax', https_only=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')

app.include_router(health_router)
app.include_router(sync_router)
app.include_router(pages_router)
