from datetime import UTC, datetime, timedelta
import secrets
import string

from fastapi import HTTPException, status

from backend.repositories.tenant_agent_credential_repository import TenantAgentCredentialRepository
from backend.repositories.tenant_pairing_repository import TenantPairingRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.tenant_pairing import (
    TenantPairingActivateResponse,
    TenantPairingCodeCreateResponse,
)
from backend.utils.security import generate_api_key, hash_api_key, validate_empresa_id

_PAIR_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _normalize_pairing_code(code: str) -> str:
    normalized = code.strip().upper().replace("-", "").replace(" ", "")
    if len(normalized) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo de vinculacao invalido.",
        )
    allowed = set(string.ascii_uppercase + string.digits)
    if not set(normalized).issubset(allowed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Codigo de vinculacao invalido.",
        )
    return normalized


def _format_pairing_code(raw: str) -> str:
    if len(raw) <= 4:
        return raw
    chunks = [raw[i : i + 4] for i in range(0, len(raw), 4)]
    return "-".join(chunks)


class TenantPairingService:
    def __init__(
        self,
        tenant_repository: TenantRepository,
        pairing_repository: TenantPairingRepository,
        credential_repository: TenantAgentCredentialRepository,
    ):
        self.tenant_repository = tenant_repository
        self.pairing_repository = pairing_repository
        self.credential_repository = credential_repository

    def create_pairing_code(
        self,
        *,
        empresa_id: str,
        ttl_minutes: int,
        actor: str = "system",
    ) -> TenantPairingCodeCreateResponse:
        if not validate_empresa_id(empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )
        tenant = self.tenant_repository.get_active_tenant(empresa_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant nao encontrado.",
            )

        raw_code = "".join(secrets.choice(_PAIR_ALPHABET) for _ in range(8))
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
        self.pairing_repository.create_code(
            empresa_id=empresa_id,
            code_hash=hash_api_key(raw_code),
            expires_at=expires_at,
            created_by=actor,
        )
        return TenantPairingCodeCreateResponse(
            empresa_id=empresa_id,
            pairing_code=_format_pairing_code(raw_code),
            expires_at=expires_at,
            status="ok",
        )

    def activate_pairing_code(
        self,
        *,
        pairing_code: str,
        device_label: str,
    ) -> TenantPairingActivateResponse:
        normalized = _normalize_pairing_code(pairing_code)
        item = self.pairing_repository.get_active_by_hash(hash_api_key(normalized))
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Codigo de vinculacao invalido ou expirado.",
            )
        tenant = self.tenant_repository.get_active_tenant(item.empresa_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant nao encontrado.",
            )

        raw_api_key = generate_api_key()
        self.credential_repository.create(
            empresa_id=item.empresa_id,
            device_label=device_label.strip() or "local-agent",
            api_key_hash=hash_api_key(raw_api_key),
        )
        self.pairing_repository.mark_used(item, used_by=device_label.strip() or "local-agent")
        return TenantPairingActivateResponse(
            empresa_id=item.empresa_id,
            api_key=raw_api_key,
            status="ok",
        )
