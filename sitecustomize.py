from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SHARED_SRC = ROOT / "packages" / "shared" / "src"

if SHARED_SRC.exists():
    shared_path = str(SHARED_SRC)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)
