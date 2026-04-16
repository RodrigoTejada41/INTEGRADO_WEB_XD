from __future__ import annotations

import csv
import io


def records_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['id', 'batch_id', 'record_key', 'record_type', 'event_time', 'created_at'])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue()


def audit_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'source', 'event', 'detail'])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return output.getvalue()
