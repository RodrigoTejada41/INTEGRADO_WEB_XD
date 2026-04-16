from __future__ import annotations

import json
from typing import Any

from shared.db import get_conn
from shared.utils import utc_now


def publish(event_type: str, payload: dict[str, Any]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO event_queue(event_type, payload_json, created_at, processed_at) VALUES(?,?,?,NULL)",
            (event_type, json.dumps(payload, ensure_ascii=True), utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)


def consume_one(event_type: str) -> tuple[int, dict[str, Any]] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, payload_json FROM event_queue WHERE event_type=? AND processed_at IS NULL ORDER BY id LIMIT 1",
            (event_type,),
        ).fetchone()
        if not row:
            return None
        conn.execute("UPDATE event_queue SET processed_at=? WHERE id=?", (utc_now(), row['id']))
        conn.commit()
        return int(row['id']), json.loads(row['payload_json'])
