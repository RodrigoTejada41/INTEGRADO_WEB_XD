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

from shared.config import NEXUS_MANIFEST_PATH, OBSIDIAN_VAULT_PATH
from shared.db import get_conn, init_db
from shared.events import consume_one
from shared.utils import sha256_text, utc_now


def _write_obsidian_note(dataset_id: int, source_path: str, semver: str, payload: dict) -> Path:
    folder = OBSIDIAN_VAULT_PATH / '03-datasets'
    folder.mkdir(parents=True, exist_ok=True)
    note_path = folder / f'dataset-{dataset_id}.md'
    content = (
        '---\n'
        f'id: dataset-{dataset_id}\n'
        'type: dataset-version\n'
        f'version: {semver}\n'
        f'source_file: {source_path}\n'
        f'generated_at: {utc_now()}\n'
        'tags: [dataset, reverse-engineering, pipeline]\n'
        '---\n\n'
        f'# Dataset {dataset_id} ({semver})\n\n'
        '## Summary\n'
        'Structured data generated from reverse engineering knowledge source.\n\n'
        '## Payload\n'
        '```json\n'
        f"{json.dumps(payload, ensure_ascii=True, indent=2)}\n"
        '```\n'
    )
    note_path.write_text(content, encoding='utf-8')
    return note_path


def _write_nexus_manifest(dataset_id: int, semver: str, normalized_json: str) -> Path:
    folder = NEXUS_MANIFEST_PATH / 'snapshots'
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / f'dataset-{dataset_id}-{semver}.json'
    checksum = sha256_text(normalized_json)
    manifest = {
        'dataset_version_id': dataset_id,
        'semantic_version': semver,
        'created_at': utc_now(),
        'checksum_sha256': checksum,
        'artifact_kind': 'dataset-snapshot',
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2), encoding='utf-8')
    return manifest_path


def process_one() -> bool:
    event = consume_one('DATA_TRANSFORMED')
    if not event:
        return False

    _, payload = event
    dataset_id = int(payload['dataset_version_id'])

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT dv.id, dv.source_file_id, dv.semver, dv.normalized_json, sf.source_path
            FROM dataset_versions dv
            JOIN source_files sf ON sf.id = dv.source_file_id
            WHERE dv.id=?
            """,
            (dataset_id,),
        ).fetchone()
        if not row:
            return False

        normalized = json.loads(row['normalized_json'])
        note_path = _write_obsidian_note(dataset_id, row['source_path'], row['semver'], normalized)
        manifest_path = _write_nexus_manifest(dataset_id, row['semver'], row['normalized_json'])

        conn.execute(
            'INSERT INTO artifacts(dataset_version_id, artifact_type, artifact_path, checksum_sha256, created_at) VALUES(?,?,?,?,?)',
            (dataset_id, 'obsidian-note', str(note_path), sha256_text(note_path.read_text(encoding='utf-8')), utc_now()),
        )
        conn.execute(
            'INSERT INTO artifacts(dataset_version_id, artifact_type, artifact_path, checksum_sha256, created_at) VALUES(?,?,?,?,?)',
            (dataset_id, 'nexus-manifest', str(manifest_path), sha256_text(manifest_path.read_text(encoding='utf-8')), utc_now()),
        )
        conn.execute(
            'INSERT INTO processing_jobs(source_file_id, stage, status, started_at, ended_at, message) VALUES(?,?,?,?,?,?)',
            (row['source_file_id'], 'persistence', 'completed', utc_now(), utc_now(), 'Obsidian and Nexus artifacts created'),
        )
        conn.commit()

    return True


def process_all_available() -> int:
    count = 0
    while process_one():
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Process all pending DATA_TRANSFORMED events and exit.')
    args = parser.parse_args()

    init_db()
    print('[persistence] ready')

    if args.once:
        count = process_all_available()
        print(f'[persistence] processed={count}')
        return

    while True:
        if not process_one():
            time.sleep(2)


if __name__ == '__main__':
    main()
