from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


def _prepare_sync_admin(db_name: str) -> None:
    db_path = Path(f"output/{db_name}")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"output/{db_name}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_scope_columns_and_branch_permission_table_exist() -> None:
    _prepare_sync_admin("test_scope_schema.db")

    from app.core.db import Base
    from app.models import User, UserBranchPermission  # noqa: F401

    db_path = Path("output/test_scope_schema_assert.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    permission_columns = {column["name"] for column in inspector.get_columns("user_branch_permissions")}

    assert "scope_type" in user_columns
    assert "user_branch_permissions" in inspector.get_table_names()
    assert {"user_id", "empresa_id", "branch_code", "can_view_reports"} <= permission_columns
