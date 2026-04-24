from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

SYNC_ADMIN_ROOT = Path("sync-admin").resolve()
if str(SYNC_ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SYNC_ADMIN_ROOT))

from app.core.db import Base
from app.services import remote_agent_service as remote_agent_module
from app.services.remote_agent_service import RemoteAgentService


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return factory()


def test_remote_agent_cycle_skips_when_pull_is_disabled(monkeypatch) -> None:
    session = _session()
    service = RemoteAgentService(session)

    called = {"register": 0, "heartbeat": 0, "pull": 0}

    async def _register_if_possible() -> None:
        called["register"] += 1

    async def _send_heartbeat() -> None:
        called["heartbeat"] += 1

    async def _pull_and_execute_commands() -> None:
        called["pull"] += 1

    monkeypatch.setattr(remote_agent_module.settings, "remote_command_pull_enabled", False)
    monkeypatch.setattr(service, "register_if_possible", _register_if_possible)
    monkeypatch.setattr(service, "send_heartbeat", _send_heartbeat)
    monkeypatch.setattr(service, "pull_and_execute_commands", _pull_and_execute_commands)

    import asyncio

    asyncio.run(service.run_remote_cycle())

    assert called == {"register": 0, "heartbeat": 0, "pull": 0}


def test_remote_agent_status_snapshot_includes_command_state() -> None:
    session = _session()
    service = RemoteAgentService(session)

    snapshot = service.build_status_snapshot()

    assert snapshot["service"] == "sync-admin"
    assert "last_command_poll_at" in snapshot
    assert "last_registration_at" in snapshot
    assert "pending_local_batches" in snapshot
    assert "total_local_records" in snapshot
