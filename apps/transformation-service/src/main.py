from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / 'packages' / 'shared' / 'src'
if SHARED_SRC.exists():
    shared_path = str(SHARED_SRC)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

from shared.db import get_conn, init_db
from shared.events import consume_one, publish
from shared.utils import to_json, utc_now


def _next_semver(conn, source_id: int) -> str:
    row = conn.execute(
        'SELECT semver FROM dataset_versions WHERE source_file_id=? ORDER BY id DESC LIMIT 1',
        (source_id,),
    ).fetchone()
    if not row:
        return '0.1.0'
    major, minor, patch = [int(x) for x in row['semver'].split('.')]
    return f'{major}.{minor}.{patch + 1}'


def process_one() -> bool:
    event = consume_one('DATA_INTERPRETED')
    if not event:
        return False

    _, payload = event
    source_id = int(payload['source_file_id'])

    with get_conn() as conn:
        row = conn.execute(
            'SELECT interpreted_json, parser_type, confidence FROM interpreted_data WHERE source_file_id=? ORDER BY id DESC LIMIT 1',
            (source_id,),
        ).fetchone()
        if not row:
            return False

        semver = _next_semver(conn, source_id)
        normalized = {
            'source_file_id': source_id,
            'parser_type': row['parser_type'],
            'confidence': row['confidence'],
            'interpreted': json.loads(row['interpreted_json']),
            'normalized_at': utc_now(),
        }
        cur = conn.execute(
            'INSERT INTO dataset_versions(source_file_id, semver, normalized_json, created_at) VALUES(?,?,?,?)',
            (source_id, semver, to_json(normalized), utc_now()),
        )
        dataset_id = int(cur.lastrowid)
        conn.execute(
            'INSERT INTO processing_jobs(source_file_id, stage, status, started_at, ended_at, message) VALUES(?,?,?,?,?,?)',
            (source_id, 'transformation', 'completed', utc_now(), utc_now(), f'Dataset {semver}'),
        )
        conn.commit()

    publish('DATA_TRANSFORMED', {'dataset_version_id': dataset_id, 'source_file_id': source_id})
    return True


def process_all_available() -> int:
    count = 0
    while process_one():
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Process all pending DATA_INTERPRETED events and exit.')
    args = parser.parse_args()

    init_db()
    print('[transform] ready')

    if args.once:
        count = process_all_available()
        print(f'[transform] processed={count}')
        return

    while True:
        if not process_one():
            time.sleep(2)


if __name__ == '__main__':
    main()
