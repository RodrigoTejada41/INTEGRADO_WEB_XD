from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_sync_admin(db_name: str) -> None:
    db_path = Path(f"output/{db_name}")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"output/{db_name}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_create_client_with_branch_scope_persists_permissions() -> None:
    _prepare_sync_admin("test_client_branch_scope_create.db")

    from app.core.db import Base, SessionLocal, engine
    from app.repositories.user_repository import UserRepository
    from app.schemas.users import UserCreateRequest
    from app.services.user_service import UserService

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        service = UserService(UserRepository(db))
        created = service.create_user(
            UserCreateRequest(
                username="cliente_filial",
                full_name="Cliente Filial",
                password="cliente123",
                role="client",
                empresa_id="55555555000155",
                scope_type="branch_set",
                allowed_branch_codes=["0001", "0003"],
            )
        )

        assert created.scope_type == "branch_set"
        assert created.allowed_branch_codes == ["0001", "0003"]


def test_update_existing_client_scope_replaces_permissions() -> None:
    _prepare_sync_admin("test_client_branch_scope_update.db")

    from app.core.db import Base, SessionLocal, engine
    from app.repositories.user_repository import UserRepository
    from app.schemas.users import UserCreateRequest, UserUpdateRequest
    from app.services.user_service import UserService

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        service = UserService(UserRepository(db))
        created = service.create_user(
            UserCreateRequest(
                username="cliente_update",
                full_name="Cliente Update",
                password="cliente123",
                role="client",
                empresa_id="55555555000155",
                scope_type="branch_set",
                allowed_branch_codes=["0001", "0003"],
            )
        )

        updated = service.update_user(
            created.id,
            UserUpdateRequest(
                full_name="Cliente Update Editado",
                role="client",
                empresa_id="55555555000155",
                scope_type="company",
                allowed_branch_codes=[],
                is_active=True,
            ),
        )

        assert updated.full_name == "Cliente Update Editado"
        assert updated.scope_type == "company"
        assert updated.allowed_branch_codes == []


def test_settings_page_updates_existing_client_scope() -> None:
    _prepare_sync_admin("test_settings_scope_update_form.db")

    from fastapi.testclient import TestClient

    from app.core.db import SessionLocal
    from app.main import app
    from app.repositories.user_repository import UserRepository
    from app.schemas.users import UserCreateRequest
    from app.services.user_service import UserService

    with SessionLocal() as db:
        created = UserService(UserRepository(db)).create_user(
            UserCreateRequest(
                username="cliente_editavel",
                full_name="Cliente Editavel",
                password="cliente123",
                role="client",
                empresa_id="55555555000155",
                scope_type="branch_set",
                allowed_branch_codes=["0001"],
            )
        )

    with TestClient(app) as client:
        login = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login.status_code in (302, 303)

        response = client.post(
            f"/settings/users/{created.id}",
            data={
                "full_name": "Cliente Editavel Atualizado",
                "role": "client",
                "empresa_id": "55555555000155",
                "scope_type": "branch_set",
                "allowed_branch_codes": ["0001", "0003"],
                "is_active": "true",
                "password": "",
            },
            follow_redirects=False,
        )

        assert response.status_code in (302, 303)

        second_response = client.post(
            f"/settings/users/{created.id}",
            data={
                "full_name": "Cliente Editavel Atualizado",
                "role": "client",
                "empresa_id": "55555555000155",
                "scope_type": "company",
                "allowed_branch_codes": [],
                "is_active": "true",
                "password": "",
            },
            follow_redirects=False,
        )

        assert second_response.status_code in (302, 303)

        settings_page = client.get("/settings")
        assert settings_page.status_code == 200
        assert "Cliente Editavel Atualizado" in settings_page.text
        assert "0001, 0003" in settings_page.text
        assert "Auditoria local de acessos" in settings_page.text
        assert "user.scope.update" in settings_page.text
        assert "cliente_editavel" in settings_page.text
        assert "Escopo:" in settings_page.text
        assert "Filiais:" in settings_page.text
        assert "empresa inteira" in settings_page.text
        assert "atencao" in settings_page.text
        assert "Escopo de acesso alterado" in settings_page.text
        assert "Filiais removidas: 0001, 0003" in settings_page.text
