from datetime import UTC, datetime, timedelta
import os
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base
from backend.models.empresa import Empresa
from backend.models.refresh_token import RefreshToken
from backend.models.user_account import UserAccount
from backend.repositories.empresa_repository import EmpresaRepository
from backend.repositories.refresh_token_repository import RefreshTokenRepository
from backend.repositories.user_account_repository import UserAccountRepository
from backend.services.auth_service import AuthService
from backend.config.settings import get_settings
from backend.utils.security import hash_password


def _session() -> Session:
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["ADMIN_TOKEN"] = "test-admin-token"
    get_settings.cache_clear()
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()


def test_authenticate_and_issue_tokens() -> None:
    session = _session()
    empresa = Empresa(id=str(uuid.uuid4()), cnpj="12345678000199", nome="Empresa Teste", ativo=True)
    session.add(empresa)
    user = UserAccount(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        email="admin@teste.com",
        nome="Admin",
        role="admin",
        password_hash=hash_password("Senha@123"),
        ativo=True,
    )
    session.add(user)
    session.commit()

    service = AuthService(UserAccountRepository(session), EmpresaRepository(session), RefreshTokenRepository(session))
    auth_user = service.authenticate("admin@teste.com", "Senha@123")
    assert auth_user.id == user.id
    tokens = service.issue_tokens(auth_user)
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.expires_in > 0


def test_refresh_token_revocation() -> None:
    session = _session()
    empresa = Empresa(id=str(uuid.uuid4()), cnpj="12345678000199", nome="Empresa Teste", ativo=True)
    user = UserAccount(
        id=str(uuid.uuid4()),
        empresa_id=empresa.id,
        email="admin@teste.com",
        nome="Admin",
        role="admin",
        password_hash=hash_password("Senha@123"),
        ativo=True,
    )
    session.add_all([empresa, user])
    session.commit()

    repo = RefreshTokenRepository(session)
    token = RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash="hash-1",
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked=False,
    )
    repo.add(token)
    session.commit()
    repo.revoke_by_user(user.id)
    session.commit()
    updated = repo.get_by_hash("hash-1")
    assert updated and updated.revoked is True
