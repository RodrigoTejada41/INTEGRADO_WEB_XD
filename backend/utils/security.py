import hashlib
import hmac
import re
import secrets

EMPRESA_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.]{3,32}$")
API_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{32,256}$")


def hash_api_key(raw_api_key: str) -> str:
    return hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_api_key: str, expected_hash: str) -> bool:
    candidate_hash = hash_api_key(raw_api_key)
    return hmac.compare_digest(candidate_hash, expected_hash)


def validate_empresa_id(empresa_id: str) -> bool:
    return bool(EMPRESA_ID_PATTERN.match(empresa_id))


def validate_api_key_format(raw_api_key: str) -> bool:
    return bool(API_KEY_PATTERN.match(raw_api_key))


def generate_api_key(size: int = 48) -> str:
    return secrets.token_urlsafe(size)
