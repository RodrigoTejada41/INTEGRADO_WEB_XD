from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT / 'packages' / 'shared' / 'src'
if SHARED_SRC.exists():
    shared_path = str(SHARED_SRC)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

from shared.config import (
    AUTH_USERS,
    JWT_ACCESS_EXPIRES_MINUTES,
    JWT_ALGORITHM,
    JWT_REFRESH_EXPIRES_MINUTES,
    JWT_SECRET,
)
from shared.db import get_conn, init_db
from shared.utils import to_json, utc_now

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title='Reverse Engineering Data API', version='1.2.0', lifespan=lifespan)

ROLE_SCOPES = {
    'admin': {
        'files:read',
        'jobs:read',
        'datasets:read',
        'reports:read',
        'audit:read',
    },
    'analyst': {
        'files:read',
        'jobs:read',
        'datasets:read',
        'reports:read',
    },
    'viewer': {
        'datasets:read',
        'reports:read',
    },
}


class TokenRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    access_expires_in_seconds: int
    refresh_expires_in_seconds: int
    role: str


class CurrentUser(BaseModel):
    username: str
    role: str
    scopes: list[str]
    access_jti: str


def _audit(actor: str, action: str, entity_type: str, entity_id: str, metadata: dict[str, Any] | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO audit_events(actor, action, entity_type, entity_id, metadata_json, created_at) VALUES(?,?,?,?,?,?)',
            (actor, action, entity_type, entity_id, to_json(metadata or {}), utc_now()),
        )
        conn.commit()


def _to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _is_revoked(jti: str) -> bool:
    with get_conn() as conn:
        row = conn.execute('SELECT id FROM revoked_tokens WHERE jti=?', (jti,)).fetchone()
    return row is not None


def _revoke_jti(jti: str, token_type: str, reason: str, expires_at_iso: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO revoked_tokens(jti, token_type, reason, expires_at, revoked_at) VALUES(?,?,?,?,?)',
            (jti, token_type, reason, expires_at_iso, utc_now()),
        )
        conn.commit()


def _build_token(username: str, role: str, token_type: str) -> tuple[str, int, str]:
    scopes = sorted(list(ROLE_SCOPES.get(role, set()))) if token_type == 'access' else []
    now = datetime.now(timezone.utc)
    expire_minutes = JWT_ACCESS_EXPIRES_MINUTES if token_type == 'access' else JWT_REFRESH_EXPIRES_MINUTES
    exp = now + timedelta(minutes=expire_minutes)
    jti = str(uuid.uuid4())
    payload = {
        'sub': username,
        'role': role,
        'type': token_type,
        'jti': jti,
        'scopes': scopes,
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, int(exp.timestamp()), jti


def _decode_raw(token: str, expected_type: str | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f'Invalid token: {exc}') from exc

    jti = str(payload.get('jti', '')).strip()
    token_type = str(payload.get('type', '')).strip()

    if not jti or not token_type:
        raise HTTPException(status_code=401, detail='Invalid token payload')

    if expected_type and token_type != expected_type:
        raise HTTPException(status_code=401, detail=f'Invalid token type: expected {expected_type}')

    if _is_revoked(jti):
        raise HTTPException(status_code=401, detail='Token revoked')

    return payload


def _store_refresh_token(jti: str, username: str, role: str, exp_ts: int) -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT OR IGNORE INTO refresh_tokens(jti, username, role, expires_at, revoked_at, used_at, created_at) VALUES(?,?,?,?,?,?,?)',
            (jti, username, role, _to_iso(exp_ts), None, None, utc_now()),
        )
        conn.commit()


def _mark_refresh_used_and_revoked(jti: str) -> None:
    with get_conn() as conn:
        row = conn.execute(
            'SELECT jti, expires_at, revoked_at, used_at FROM refresh_tokens WHERE jti=?',
            (jti,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail='Unknown refresh token')
        if row['revoked_at'] is not None or row['used_at'] is not None:
            raise HTTPException(status_code=401, detail='Refresh token already used/revoked')
        conn.execute('UPDATE refresh_tokens SET used_at=?, revoked_at=? WHERE jti=?', (utc_now(), utc_now(), jti))
        conn.commit()


def _decode_access_token(token: str) -> CurrentUser:
    payload = _decode_raw(token, expected_type='access')

    username = str(payload.get('sub', '')).strip()
    role = str(payload.get('role', '')).strip()
    scopes = payload.get('scopes', [])
    access_jti = str(payload.get('jti', '')).strip()

    if not username or not role or not isinstance(scopes, list) or not access_jti:
        raise HTTPException(status_code=401, detail='Invalid token payload')

    return CurrentUser(username=username, role=role, scopes=[str(s) for s in scopes], access_jti=access_jti)


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing Bearer token')
    return authorization[7:].strip()


def current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    token = _extract_bearer(authorization)
    return _decode_access_token(token)


def require_scope(scope: str):
    def checker(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if scope not in set(user.scopes):
            raise HTTPException(status_code=403, detail=f'Missing scope: {scope}')
        return user

    return checker


def _issue_token_pair(username: str, role: str) -> TokenPairResponse:
    access_token, access_exp_ts, _ = _build_token(username, role, token_type='access')
    refresh_token, refresh_exp_ts, refresh_jti = _build_token(username, role, token_type='refresh')
    _store_refresh_token(refresh_jti, username, role, refresh_exp_ts)
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_in_seconds=max(0, access_exp_ts - int(datetime.now(timezone.utc).timestamp())),
        refresh_expires_in_seconds=max(0, refresh_exp_ts - int(datetime.now(timezone.utc).timestamp())),
        role=role,
    )


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.post('/auth/token', response_model=TokenPairResponse)
def login(body: TokenRequest) -> TokenPairResponse:
    rec = AUTH_USERS.get(body.username)
    if not rec or rec.get('password') != body.password:
        raise HTTPException(status_code=401, detail='Invalid credentials')

    role = rec.get('role', 'viewer')
    pair = _issue_token_pair(body.username, role)
    _audit(body.username, 'login_success', 'auth', body.username, {'role': role})
    return pair


@app.post('/auth/refresh', response_model=TokenPairResponse)
def refresh(body: RefreshRequest) -> TokenPairResponse:
    payload = _decode_raw(body.refresh_token, expected_type='refresh')

    refresh_jti = str(payload.get('jti', '')).strip()
    username = str(payload.get('sub', '')).strip()
    role = str(payload.get('role', '')).strip()
    refresh_exp_ts = int(payload.get('exp', 0))

    if not refresh_jti or not username or not role:
        raise HTTPException(status_code=401, detail='Invalid refresh token payload')

    _mark_refresh_used_and_revoked(refresh_jti)
    _revoke_jti(refresh_jti, 'refresh', 'rotated', _to_iso(refresh_exp_ts))

    pair = _issue_token_pair(username, role)
    _audit(username, 'refresh_success', 'auth', username, {'previous_refresh_jti': refresh_jti})
    return pair


@app.post('/auth/logout')
def logout(
    body: LogoutRequest,
    authorization: str | None = Header(default=None),
    user: CurrentUser = Depends(current_user),
) -> dict[str, str]:
    access_token = _extract_bearer(authorization)
    access_payload = _decode_raw(access_token, expected_type='access')
    access_jti = str(access_payload.get('jti', '')).strip()
    access_exp_ts = int(access_payload.get('exp', 0))

    _revoke_jti(access_jti, 'access', 'logout', _to_iso(access_exp_ts) if access_exp_ts else None)

    if body.refresh_token:
        refresh_payload = _decode_raw(body.refresh_token, expected_type='refresh')
        refresh_jti = str(refresh_payload.get('jti', '')).strip()
        refresh_exp_ts = int(refresh_payload.get('exp', 0))

        with get_conn() as conn:
            conn.execute(
                'UPDATE refresh_tokens SET revoked_at=COALESCE(revoked_at, ?) WHERE jti=?',
                (utc_now(), refresh_jti),
            )
            conn.commit()

        _revoke_jti(refresh_jti, 'refresh', 'logout', _to_iso(refresh_exp_ts) if refresh_exp_ts else None)

    _audit(user.username, 'logout', 'auth', user.username, None)
    return {'status': 'logged_out'}


@app.get('/api/v1/auth/me')
def me(user: CurrentUser = Depends(current_user)) -> dict[str, Any]:
    return user.model_dump()


@app.get('/api/v1/files')
def list_files(limit: int = 200, user: CurrentUser = Depends(require_scope('files:read'))) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT id, source_path, file_name, extension, file_hash, size_bytes, discovered_at FROM source_files ORDER BY id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    _audit(user.username, 'read_files', 'source_files', str(limit), None)
    return [dict(r) for r in rows]


@app.get('/api/v1/jobs')
def list_jobs(limit: int = 300, user: CurrentUser = Depends(require_scope('jobs:read'))) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT id, source_file_id, stage, status, started_at, ended_at, message FROM processing_jobs ORDER BY id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    _audit(user.username, 'read_jobs', 'processing_jobs', str(limit), None)
    return [dict(r) for r in rows]


@app.get('/api/v1/datasets')
def list_datasets(limit: int = 200, user: CurrentUser = Depends(require_scope('datasets:read'))) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT id, source_file_id, semver, created_at FROM dataset_versions ORDER BY id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    _audit(user.username, 'read_datasets', 'dataset_versions', str(limit), None)
    return [dict(r) for r in rows]


@app.get('/api/v1/datasets/{dataset_id}')
def get_dataset(dataset_id: int, user: CurrentUser = Depends(require_scope('datasets:read'))) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            'SELECT id, source_file_id, semver, normalized_json, created_at FROM dataset_versions WHERE id=?',
            (dataset_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail='Not found')
    out = dict(row)
    out['normalized_json'] = json.loads(out['normalized_json'])
    _audit(user.username, 'read_dataset', 'dataset_versions', str(dataset_id), None)
    return out


@app.get('/api/v1/reports/summary')
def summary(user: CurrentUser = Depends(require_scope('reports:read'))) -> dict[str, Any]:
    with get_conn() as conn:
        files = conn.execute('SELECT COUNT(*) c FROM source_files').fetchone()['c']
        datasets = conn.execute('SELECT COUNT(*) c FROM dataset_versions').fetchone()['c']
        artifacts = conn.execute('SELECT COUNT(*) c FROM artifacts').fetchone()['c']
        jobs = conn.execute('SELECT COUNT(*) c FROM processing_jobs').fetchone()['c']
    _audit(user.username, 'read_report_summary', 'reports', 'summary', None)
    return {
        'source_files': files,
        'dataset_versions': datasets,
        'artifacts': artifacts,
        'jobs': jobs,
    }


@app.get('/api/v1/audit-events')
def list_audit_events(limit: int = 200, user: CurrentUser = Depends(require_scope('audit:read'))) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT id, actor, action, entity_type, entity_id, metadata_json, created_at FROM audit_events ORDER BY id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
