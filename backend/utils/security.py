import hashlib
import hmac
from datetime import UTC, datetime, timedelta
import re
import secrets
from typing import Any

import jwt
from passlib.context import CryptContext

from backend.config.settings import get_settings

EMPRESA_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.]{3,32}$")
CNPJ_PATTERN = re.compile(r"^\d{14}$")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_api_key(raw_api_key: str) -> str:
    return hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_api_key: str, expected_hash: str) -> bool:
    candidate_hash = hash_api_key(raw_api_key)
    return hmac.compare_digest(candidate_hash, expected_hash)


def validate_empresa_id(empresa_id: str) -> bool:
    return bool(EMPRESA_ID_PATTERN.match(empresa_id))


def normalize_cnpj(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj or "")


def validate_cnpj(cnpj: str) -> bool:
    return bool(CNPJ_PATTERN.match(normalize_cnpj(cnpj)))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_jwt_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_api_key(size: int = 48) -> str:
    return secrets.token_urlsafe(size)
