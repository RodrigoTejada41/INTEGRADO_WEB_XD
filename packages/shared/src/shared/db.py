from __future__ import annotations

import sqlite3
from pathlib import Path

from shared.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    schema_path = Path('infra/sql/schema.sql')
    sql = schema_path.read_text(encoding='utf-8')
    with get_conn() as conn:
        conn.executescript(sql)
        conn.commit()
