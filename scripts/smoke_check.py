from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    return result.stdout


def load_api_app(root: Path):
    api_file = root / 'apps' / 'api-service' / 'src' / 'main.py'
    spec = importlib.util.spec_from_file_location('api_main_smoke', api_file)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load API module')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def main() -> int:
    root = Path.cwd()
    db_path = root / 'output' / 'system.db'

    os.environ.setdefault('DB_PATH', str(db_path))
    os.environ.setdefault('OBSIDIAN_VAULT_PATH', str(root / 'obsidian-vault'))
    os.environ.setdefault('NEXUS_MANIFEST_PATH', str(root / 'nexus-manifests'))
    os.environ.setdefault('JWT_SECRET', 'smoke-secret')
    os.environ.setdefault('JWT_ALGORITHM', 'HS256')
    os.environ.setdefault('JWT_ACCESS_EXPIRES_MINUTES', '60')
    os.environ.setdefault('JWT_REFRESH_EXPIRES_MINUTES', '120')
    os.environ.setdefault('AUTH_USERS', 'admin:admin123:admin;viewer:viewer123:viewer')

    # Reset local artifacts for deterministic smoke output.
    if db_path.exists():
        db_path.unlink()
    for p in (root / 'obsidian-vault' / '03-datasets').glob('dataset-*.md'):
        p.unlink()
    for p in (root / 'nexus-manifests' / 'snapshots').glob('dataset-*.json'):
        p.unlink()

    # Pipeline run
    run([sys.executable, 'apps/ingestion-service/src/main.py', '--once'])
    for _ in range(15):
        reverse_out = run([sys.executable, 'apps/reverse-engineering-service/src/main.py', '--once'])
        transform_out = run([sys.executable, 'apps/transformation-service/src/main.py', '--once'])
        persist_out = run([sys.executable, 'apps/persistence-service/src/main.py', '--once'])

        if 'processed=0' in reverse_out and 'processed=0' in transform_out and 'processed=0' in persist_out:
            break

    assert_true(db_path.exists(), 'DB file was not created')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    files_count = conn.execute('SELECT COUNT(*) c FROM source_files').fetchone()['c']
    jobs_count = conn.execute('SELECT COUNT(*) c FROM processing_jobs').fetchone()['c']
    datasets_count = conn.execute('SELECT COUNT(*) c FROM dataset_versions').fetchone()['c']
    artifacts_count = conn.execute('SELECT COUNT(*) c FROM artifacts').fetchone()['c']
    conn.close()

    assert_true(files_count > 0, 'No source files were ingested')
    assert_true(jobs_count > 0, 'No processing jobs were created')
    assert_true(datasets_count > 0, 'No datasets were generated')
    assert_true(artifacts_count > 0, 'No artifacts were generated')

    notes = list((root / 'obsidian-vault' / '03-datasets').glob('dataset-*.md'))
    manifests = list((root / 'nexus-manifests' / 'snapshots').glob('dataset-*.json'))
    assert_true(len(notes) > 0, 'No Obsidian dataset notes found')
    assert_true(len(manifests) > 0, 'No Nexus snapshot manifests found')

    # API auth and endpoint smoke with TestClient
    app = load_api_app(root)
    with TestClient(app) as client:
        health = client.get('/health')
        assert_true(health.status_code == 200, f'Health failed: {health.status_code}')

        login = client.post('/auth/token', json={'username': 'admin', 'password': 'admin123'})
        assert_true(login.status_code == 200, f'Login failed: {login.status_code} {login.text}')
        tokens = login.json()

        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        summary = client.get('/api/v1/reports/summary', headers=headers)
        assert_true(summary.status_code == 200, f'Summary failed: {summary.status_code} {summary.text}')

        files = client.get('/api/v1/files', headers=headers)
        assert_true(files.status_code == 200, f'Files endpoint failed: {files.status_code} {files.text}')

    print('SMOKE CHECK PASS')
    print(f'files={files_count} jobs={jobs_count} datasets={datasets_count} artifacts={artifacts_count}')
    print(f'obsidian_notes={len(notes)} nexus_manifests={len(manifests)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
