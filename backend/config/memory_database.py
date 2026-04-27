from collections.abc import Generator
from datetime import datetime
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings
from backend.models.memory_base import MemoryBase

settings = get_settings()

sqlite3.register_adapter(datetime, lambda value: value.isoformat(sep=" "))

memory_url = make_url(settings.memory_database_url)
if memory_url.drivername.startswith("sqlite") and memory_url.database:
    database_path = Path(memory_url.database)
    if database_path.name != ":memory:":
        database_path.expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.memory_database_url.startswith("sqlite") else {}
memory_engine = create_engine(
    settings.memory_database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)
MemorySessionLocal = sessionmaker(
    bind=memory_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def init_memory_schema() -> None:
    MemoryBase.metadata.create_all(bind=memory_engine)


def get_memory_session() -> Generator[Session, None, None]:
    session = MemorySessionLocal()
    try:
        yield session
    finally:
        session.close()

