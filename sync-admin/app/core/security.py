from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config.settings import settings

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': subject,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm='HS256')


def verify_access_token(token: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=['HS256'])
    sub = payload.get('sub')
    if not sub:
        raise ValueError('Token without subject')
    return str(sub)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def make_key_prefix(raw_key: str) -> str:
    return raw_key[:8]


def generate_random_api_key() -> str:
    return secrets.token_urlsafe(32)
