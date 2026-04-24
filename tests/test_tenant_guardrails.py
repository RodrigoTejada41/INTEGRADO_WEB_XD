from __future__ import annotations

from backend.utils.security import (
    generate_api_key,
    validate_api_key_format,
    validate_empresa_id,
)


def test_empresa_id_validation_accepts_expected_business_ids() -> None:
    assert validate_empresa_id("12345678000199") is True
    assert validate_empresa_id("Empresa_01-AB.9") is True


def test_empresa_id_validation_rejects_invalid_values() -> None:
    assert validate_empresa_id("ab") is False
    assert validate_empresa_id("id com espaco") is False
    assert validate_empresa_id("id;drop table") is False
    assert validate_empresa_id("x" * 33) is False


def test_api_key_validation_accepts_generated_keys() -> None:
    api_key = generate_api_key()

    assert len(api_key) >= 32
    assert validate_api_key_format(api_key) is True


def test_api_key_validation_rejects_invalid_values() -> None:
    assert validate_api_key_format("short-key") is False
    assert validate_api_key_format("invalid key with spaces") is False
    assert validate_api_key_format("!@#invalid") is False
