from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / 'packages' / 'shared' / 'src'
if SHARED_SRC.exists():
    shared_path = str(SHARED_SRC)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

from shared.config import KNOWLEDGE_SOURCE_PATHS, MAX_FILES_PER_SOURCE
from shared.db import get_conn, init_db
from shared.events import publish
from shared.utils import sha256_file, utc_now

SUPPORTED = {'.md', '.json', '.txt'}
FAST_FILE_FINGERPRINT = os.getenv('FAST_FILE_FINGERPRINT', '0') == '1'


def _list_supported_files(base: Path, limit: int = 0) -> list[Path]:
    if not base.exists() or not base.is_dir():
        return []

    out: list[Path] = []
    patterns = ('*.md', '*.json', '*.txt')
    for pattern in patterns:
        for p in base.rglob(pattern):
            if p.is_file() and p.suffix.lower() in SUPPORTED:
                out.append(p)
                if limit > 0 and len(out) >= limit:
                    return out
    return out


def scan_once() -> int:
    inserted = 0
    files: list[Path] = []
    for source in KNOWLEDGE_SOURCE_PATHS:
        files.extend(_list_supported_files(source, MAX_FILES_PER_SOURCE))

    with get_conn() as conn:
        for path in files:
            file_hash = _file_fingerprint(path)
            row = conn.execute(
                'SELECT id FROM source_files WHERE source_path=? AND file_hash=?',
                (str(path), file_hash),
            ).fetchone()
            if row:
                continue

            cur = conn.execute(
                """
                INSERT INTO source_files(source_path, file_name, extension, file_hash, size_bytes, discovered_at)
                VALUES(?,?,?,?,?,?)
                """,
                (str(path), path.name, path.suffix.lower(), file_hash, path.stat().st_size, utc_now()),
            )
            source_id = int(cur.lastrowid)
            conn.execute(
                'INSERT INTO processing_jobs(source_file_id, stage, status, started_at, ended_at, message) VALUES(?,?,?,?,?,?)',
                (source_id, 'ingestion', 'completed', utc_now(), utc_now(), 'File indexed from configured sources'),
            )
            conn.commit()
            publish('FILE_INGESTED', {'source_file_id': source_id, 'path': str(path)})
            inserted += 1
    return inserted


def _file_fingerprint(path: Path) -> str:
    if not FAST_FILE_FINGERPRINT:
        return sha256_file(path)

    # Fast fingerprint for very large knowledge bases: metadata + edge samples.
    st = path.stat()
    h = hashlib.sha256()
    h.update(str(path).encode('utf-8', errors='ignore'))
    h.update(str(st.st_size).encode('ascii'))
    h.update(str(int(st.st_mtime_ns)).encode('ascii'))
    with path.open('rb') as f:
        first = f.read(65536)
        h.update(first)
        if st.st_size > 65536:
            try:
                f.seek(max(0, st.st_size - 65536))
            except OSError:
                pass
            last = f.read(65536)
            h.update(last)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Run a single scan cycle and exit.')
    args = parser.parse_args()

    init_db()
    print(
        f'[ingestion] sources={KNOWLEDGE_SOURCE_PATHS} '
        f'max_files_per_source={MAX_FILES_PER_SOURCE} '
        f'fast_file_fingerprint={FAST_FILE_FINGERPRINT}'
    )

    if args.once:
        count = scan_once()
        print(f'[ingestion] new_files={count}')
        return

    while True:
        count = scan_once()
        if count:
            print(f'[ingestion] new_files={count}')
        time.sleep(5)


if __name__ == '__main__':
    main()
