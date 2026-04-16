from app.config.settings import settings
from app.core.db import Base, SessionLocal, engine
from app.services.auth_service import AuthService
from app.services.sync_service import SyncService


if __name__ == '__main__':
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        AuthService(db).ensure_initial_admin(settings.initial_admin_username, settings.initial_admin_password)
        SyncService(db).ensure_default_api_key(settings.integration_api_key)
    print('Database initialized successfully.')
