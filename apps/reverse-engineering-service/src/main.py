from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / 'packages' / 'shared' / 'src'
if SHARED_SRC.exists():
    shared_path = str(SHARED_SRC)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

from shared.db import get_conn, init_db
from shared.events import consume_one, publish
from shared.reverse_engineering import infer_file
from shared.utils import to_json, utc_now


def process_one() -> bool:
    event = consume_one('FILE_INGESTED')
    if not event:
        return False

    _, payload = event
    source_id = int(payload['source_file_id'])
    path = Path(payload['path'])
    text = path.read_text(encoding='utf-8', errors='ignore')
    parser, confidence, interpreted = infer_file(path, text)

    with get_conn() as conn:
        conn.execute(
            'INSERT INTO interpreted_data(source_file_id, parser_type, confidence, interpreted_json, created_at) VALUES(?,?,?,?,?)',
            (source_id, parser, confidence, to_json(interpreted), utc_now()),
        )
        conn.execute(
            'INSERT INTO processing_jobs(source_file_id, stage, status, started_at, ended_at, message) VALUES(?,?,?,?,?,?)',
            (source_id, 'reverse_engineering', 'completed', utc_now(), utc_now(), f'Parser={parser}'),
        )
        conn.commit()

    publish('DATA_INTERPRETED', {'source_file_id': source_id})
    return True


def process_all_available() -> int:
    count = 0
    while process_one():
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Process all pending FILE_INGESTED events and exit.')
    args = parser.parse_args()

    init_db()
    print('[reverse] ready')

    if args.once:
        count = process_all_available()
        print(f'[reverse] processed={count}')
        return

    while True:
        if not process_one():
            time.sleep(2)


if __name__ == '__main__':
    main()
