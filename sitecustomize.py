from __future__ import annotations

import os
import tempfile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SHARED_SRC = ROOT / "packages" / "shared" / "src"
PYTEST_TMP = Path(tempfile.gettempdir()) / "integrado_web_xd" / "pytest"

PYTEST_TMP.mkdir(parents=True, exist_ok=True)
for env_var in ("TMPDIR", "TEMP", "TMP"):
    current_value = os.environ.get(env_var)
    if current_value is None:
        os.environ[env_var] = str(PYTEST_TMP)
        continue

    try:
        if Path(current_value).resolve().is_relative_to(ROOT):
            os.environ[env_var] = str(PYTEST_TMP)
    except OSError:
        os.environ[env_var] = str(PYTEST_TMP)

if SHARED_SRC.exists():
    shared_path = str(SHARED_SRC)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)
