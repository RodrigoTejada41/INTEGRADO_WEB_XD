from __future__ import annotations

import base64
import hashlib
import json
import os
from functools import lru_cache

from cryptography.fernet import Fernet

from backend.config.settings import get_settings


def _derive_key_material() -> bytes:
    explicit_key = os.getenv("TENANT_CONFIG_ENCRYPTION_KEY")
    if explicit_key:
        return explicit_key.encode("utf-8")

    settings = get_settings()
    seed = settings.admin_token.encode("utf-8")
    digest = hashlib.sha256(seed).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache
def get_fernet() -> Fernet:
    return Fernet(_derive_key_material())


def encrypt_text(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def encrypt_json(payload: dict[str, str]) -> str:
    return encrypt_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def decrypt_json(payload: str) -> dict[str, str]:
    if not payload:
        return {}
    return json.loads(decrypt_text(payload))
