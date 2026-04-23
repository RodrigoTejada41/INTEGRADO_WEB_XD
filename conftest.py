from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


TEST_TMP_ROOT = Path(__file__).resolve().parent / "runtime" / "pytest-tmp"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)

tempfile.tempdir = str(TEST_TMP_ROOT)
os.environ["PYTEST_DEBUG_TEMPROOT"] = str(TEST_TMP_ROOT)
for env_var in ("TMPDIR", "TEMP", "TMP"):
    os.environ[env_var] = str(TEST_TMP_ROOT)


@pytest.fixture(autouse=True)
def restore_environment() -> None:
    original_environ = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture(autouse=True)
def dispose_backend_database_engine() -> None:
    yield

    try:
        from backend.config.database import engine
    except Exception:
        return

    engine.dispose()
