from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings import settings


class Base(DeclarativeBase):
    pass


connect_args = {'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_compatible_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if 'users' in table_names:
        user_columns = {column['name'] for column in inspector.get_columns('users')}
        if 'scope_type' not in user_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN scope_type VARCHAR(32)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
