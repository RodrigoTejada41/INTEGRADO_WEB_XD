# Client Access Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate the admin console from the client portal and enforce report visibility by `empresa_id` plus branch scope (`company` or `branch_set`) in the `sync-admin` application.

**Architecture:** Extend the local `sync-admin` identity model with explicit access scope, persist branch permissions in a dedicated relational table, and centralize scope resolution in one backend service so client routes never trust query parameters for tenant access. Keep admin behavior global, keep client behavior tenant-bound, and treat `0001` as matrix plus `0002+` as branch codes.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Jinja2 templates, SQLite/PostgreSQL via `Base.metadata.create_all`, pytest, TestClient

---

## File map

### Existing files to modify

- `sync-admin/app/models/user.py`
- `sync-admin/app/models/__init__.py`
- `sync-admin/app/repositories/user_repository.py`
- `sync-admin/app/schemas/users.py`
- `sync-admin/app/services/user_service.py`
- `sync-admin/app/services/auth_service.py`
- `sync-admin/app/web/deps.py`
- `sync-admin/app/web/routes/pages.py`
- `sync-admin/app/templates/settings.html`
- `sync-admin/app/templates/client_reports.html`
- `sync-admin/app/templates/client_dashboard.html`
- `sync-admin/app/templates/connected_apis.html`
- `tests/test_sync_admin_client_portal.py`

### New files to create

- `sync-admin/app/models/user_branch_permission.py`
- `sync-admin/app/repositories/user_branch_permission_repository.py`
- `sync-admin/app/services/client_scope_service.py`
- `tests/test_sync_admin_client_scope.py`
- `tests/test_sync_admin_settings_client_scope.py`

### Existing files to inspect while implementing

- `sync-admin/app/main.py`
- `sync-admin/app/core/db.py`
- `sync-admin/app/services/control_service.py`

---

### Task 1: Add explicit scope fields and branch permission table

**Files:**
- Create: `sync-admin/app/models/user_branch_permission.py`
- Modify: `sync-admin/app/models/user.py`
- Modify: `sync-admin/app/models/__init__.py`
- Test: `tests/test_sync_admin_client_scope.py`

- [ ] **Step 1: Write the failing model/bootstrap test**

```python
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.models import User, UserBranchPermission


def test_scope_columns_and_branch_permission_table_exist():
    db_path = Path("output/test_scope_schema.db")
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite+pysqlite:///{db_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    permission_columns = {column["name"] for column in inspector.get_columns("user_branch_permissions")}

    assert "scope_type" in user_columns
    assert "user_branch_permissions" in inspector.get_table_names()
    assert {"user_id", "empresa_id", "branch_code", "can_view_reports"} <= permission_columns
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_sync_admin_client_scope.py::test_scope_columns_and_branch_permission_table_exist -v`

Expected: FAIL because `UserBranchPermission` and `scope_type` do not exist yet.

- [ ] **Step 3: Add the new model and wire it into metadata**

```python
# sync-admin/app/models/user.py
from sqlalchemy import Boolean, DateTime, Integer, String

class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default='Administrator')
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default='admin')
    empresa_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    scope_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

```python
# sync-admin/app/models/user_branch_permission.py
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserBranchPermission(Base):
    __tablename__ = "user_branch_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "empresa_id", "branch_code", name="uq_user_branch_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    empresa_id: Mapped[str] = mapped_column(String(32), index=True)
    branch_code: Mapped[str] = mapped_column(String(16), index=True)
    can_view_reports: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
```

```python
# sync-admin/app/models/__init__.py
from app.models.user import User
from app.models.user_branch_permission import UserBranchPermission

__all__ = [
    "User",
    "UserBranchPermission",
    "IntegrationKey",
    "LocalRuntimeSetting",
    "RemoteCommandLog",
    "SyncBatch",
    "SyncRecord",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3 -m pytest tests/test_sync_admin_client_scope.py::test_scope_columns_and_branch_permission_table_exist -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sync-admin/app/models/user.py sync-admin/app/models/user_branch_permission.py sync-admin/app/models/__init__.py tests/test_sync_admin_client_scope.py
git commit -m "feat: adiciona escopo de cliente por filial"
```

### Task 2: Persist scope type and branch permissions in repositories and schemas

**Files:**
- Create: `sync-admin/app/repositories/user_branch_permission_repository.py`
- Modify: `sync-admin/app/repositories/user_repository.py`
- Modify: `sync-admin/app/schemas/users.py`
- Modify: `sync-admin/app/services/user_service.py`
- Test: `tests/test_sync_admin_settings_client_scope.py`

- [ ] **Step 1: Write the failing service test for client creation**

```python
def test_create_client_with_branch_scope_persists_permissions():
    _prepare_sync_admin("test_client_branch_scope_create.db")

    from app.core.db import SessionLocal
    from app.repositories.user_branch_permission_repository import UserBranchPermissionRepository
    from app.repositories.user_repository import UserRepository
    from app.schemas.users import UserCreateRequest
    from app.services.user_service import UserService

    with SessionLocal() as db:
        service = UserService(UserRepository(db), UserBranchPermissionRepository(db))
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py::test_create_client_with_branch_scope_persists_permissions -v`

Expected: FAIL because schema and service do not accept `scope_type` or `allowed_branch_codes`.

- [ ] **Step 3: Implement repository and schema support**

```python
# sync-admin/app/schemas/users.py
class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="viewer", min_length=3, max_length=50)
    empresa_id: str | None = Field(default=None, min_length=8, max_length=32)
    scope_type: str | None = Field(default=None, pattern="^(company|branch_set)$")
    allowed_branch_codes: list[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str
    empresa_id: str | None = None
    scope_type: str | None = None
    allowed_branch_codes: list[str] = []
    is_active: bool
    last_login_at: datetime | None = None
```

```python
# sync-admin/app/repositories/user_branch_permission_repository.py
from sqlalchemy import delete, select

class UserBranchPermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace_permissions(self, *, user_id: int, empresa_id: str, branch_codes: list[str]) -> None:
        self.db.execute(delete(UserBranchPermission).where(UserBranchPermission.user_id == user_id))
        for branch_code in sorted(set(branch_codes)):
            self.db.add(
                UserBranchPermission(
                    user_id=user_id,
                    empresa_id=empresa_id,
                    branch_code=branch_code,
                    can_view_reports=True,
                )
            )

    def list_branch_codes(self, *, user_id: int) -> list[str]:
        stmt = (
            select(UserBranchPermission.branch_code)
            .where(UserBranchPermission.user_id == user_id, UserBranchPermission.can_view_reports.is_(True))
            .order_by(UserBranchPermission.branch_code.asc())
        )
        return list(self.db.scalars(stmt).all())
```

```python
# sync-admin/app/services/user_service.py
class UserService:
    ALLOWED_ROLES = {"admin", "analyst", "viewer", "client"}
    CLIENT_SCOPE_TYPES = {"company", "branch_set"}

    def __init__(self, repository: UserRepository, branch_repository: UserBranchPermissionRepository):
        self.repository = repository
        self.branch_repository = branch_repository

    def create_user(self, payload: UserCreateRequest) -> UserResponse:
        if payload.role == "client":
            if not payload.empresa_id:
                raise HTTPException(status_code=400, detail="empresa_id obrigatorio para client.")
            if payload.scope_type not in self.CLIENT_SCOPE_TYPES:
                raise HTTPException(status_code=400, detail="scope_type obrigatorio para client.")
            if payload.scope_type == "branch_set" and not payload.allowed_branch_codes:
                raise HTTPException(status_code=400, detail="Filiais obrigatorias para branch_set.")

        user = self.repository.create(
            username=payload.username,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
            empresa_id=payload.empresa_id,
            scope_type=payload.scope_type,
        )
        if payload.role == "client" and payload.scope_type == "branch_set":
            self.branch_repository.replace_permissions(
                user_id=user.id,
                empresa_id=payload.empresa_id,
                branch_codes=payload.allowed_branch_codes,
            )
            self.repository.db.commit()
            self.repository.db.refresh(user)
        return self._to_response(user)
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py::test_create_client_with_branch_scope_persists_permissions -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sync-admin/app/repositories/user_branch_permission_repository.py sync-admin/app/repositories/user_repository.py sync-admin/app/schemas/users.py sync-admin/app/services/user_service.py tests/test_sync_admin_settings_client_scope.py
git commit -m "feat: persiste escopo e permissoes de filiais"
```

### Task 3: Centralize client scope resolution in one service

**Files:**
- Create: `sync-admin/app/services/client_scope_service.py`
- Modify: `sync-admin/app/web/deps.py`
- Modify: `sync-admin/app/services/auth_service.py`
- Test: `tests/test_sync_admin_client_scope.py`

- [ ] **Step 1: Write the failing scope resolution tests**

```python
def test_client_scope_service_returns_all_branches_for_company_scope():
    service = ClientScopeService(
        control_service=FakeControlService(branches=["0001", "0002", "0003"]),
        branch_repository=FakeBranchRepository([]),
    )

    result = service.resolve(
        user=SimpleNamespace(id=7, empresa_id="55555555000155", role="client", scope_type="company"),
        requested_branch_code=None,
    )

    assert result.empresa_id == "55555555000155"
    assert result.allowed_branch_codes == ["0001", "0002", "0003"]
    assert result.selected_branch_code is None


def test_client_scope_service_blocks_branch_outside_allowed_scope():
    service = ClientScopeService(
        control_service=FakeControlService(branches=["0001", "0002", "0003"]),
        branch_repository=FakeBranchRepository(["0001", "0003"]),
    )

    with pytest.raises(HTTPException) as exc:
        service.resolve(
            user=SimpleNamespace(id=9, empresa_id="55555555000155", role="client", scope_type="branch_set"),
            requested_branch_code="0002",
        )

    assert exc.value.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_sync_admin_client_scope.py -v`

Expected: FAIL because `ClientScopeService` does not exist yet.

- [ ] **Step 3: Implement the scope service and keep it reusable**

```python
# sync-admin/app/services/client_scope_service.py
from dataclasses import dataclass


@dataclass
class ClientReportScope:
    empresa_id: str
    allowed_branch_codes: list[str]
    selected_branch_code: str | None


class ClientScopeService:
    def __init__(self, control_service: ControlService, branch_repository: UserBranchPermissionRepository):
        self.control_service = control_service
        self.branch_repository = branch_repository

    def resolve(self, *, user: User, requested_branch_code: str | None) -> ClientReportScope:
        if user.role != "client" or not user.empresa_id:
            raise HTTPException(status_code=403, detail="Acesso restrito ao portal do cliente.")

        available = self._fetch_company_branch_codes(user.empresa_id)
        if user.scope_type == "company":
            allowed = available
        else:
            allowed = [code for code in self.branch_repository.list_branch_codes(user_id=user.id) if code in available]

        if requested_branch_code and requested_branch_code not in allowed:
            raise HTTPException(status_code=403, detail="Filial fora do escopo autorizado.")

        return ClientReportScope(
            empresa_id=user.empresa_id,
            allowed_branch_codes=allowed,
            selected_branch_code=requested_branch_code or None,
        )
```

- [ ] **Step 4: Run the scope tests**

Run: `py -3 -m pytest tests/test_sync_admin_client_scope.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sync-admin/app/services/client_scope_service.py sync-admin/app/web/deps.py sync-admin/app/services/auth_service.py tests/test_sync_admin_client_scope.py
git commit -m "feat: centraliza resolucao de escopo do cliente"
```

### Task 4: Apply the centralized scope to client report pages

**Files:**
- Modify: `sync-admin/app/web/routes/pages.py`
- Modify: `sync-admin/app/templates/client_reports.html`
- Modify: `sync-admin/app/templates/client_dashboard.html`
- Test: `tests/test_sync_admin_client_portal.py`

- [ ] **Step 1: Write the failing integration test for branch filtering**

```python
def test_client_reports_only_expose_authorized_branches(monkeypatch):
    _prepare_sync_admin("test_client_report_branch_scope.db")

    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(
        ControlService,
        "fetch_report_overview",
        lambda self, **kwargs: {
            "empresa_id": kwargs["empresa_id"],
            "total_records": 8,
            "distinct_products": 3,
            "distinct_branches": 3,
            "distinct_terminals": 2,
            "total_sales_value": "800.00",
            "first_sale_date": "2026-04-01",
            "last_sale_date": "2026-04-20",
        },
    )
    monkeypatch.setattr(ControlService, "fetch_report_daily_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_top_products", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_recent_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_branch_options", lambda self, **kwargs: {"items": ["0001", "0002", "0003"]})

    with TestClient(app) as client:
        # bootstrap admin and create branch-scoped client first
        ...
        response = client.get("/client/reports")
        assert response.status_code == 200
        assert "0001" in response.text
        assert "0003" in response.text
        assert "0002" not in response.text

        blocked = client.get("/client/reports", params={"branch_code": "0002"})
        assert blocked.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_sync_admin_client_portal.py::test_client_reports_only_expose_authorized_branches -v`

Expected: FAIL because the client routes still trust raw branch filters and do not expose allowed branches.

- [ ] **Step 3: Implement route-level scope enforcement**

```python
# sync-admin/app/web/routes/pages.py
def client_reports_page(...):
    scope = ClientScopeService(ControlService(), UserBranchPermissionRepository(db)).resolve(
        user=current_user,
        requested_branch_code=branch_code,
    )
    payload = _build_report_payload(
        empresa_id=scope.empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=scope.selected_branch_code,
        terminal_code=terminal_code,
        top_limit=top_limit,
        recent_limit=recent_limit,
    )
    return templates.TemplateResponse(
        request,
        "client_reports.html",
        {
            "request": request,
            "current_user": current_user,
            "allowed_branch_codes": scope.allowed_branch_codes,
            **payload,
        },
    )
```

```html
<!-- sync-admin/app/templates/client_reports.html -->
<select class="form-select" name="branch_code">
  <option value="" {% if not branch_code %}selected{% endif %}>Todas as filiais permitidas</option>
  {% for allowed_code in allowed_branch_codes %}
  <option value="{{ allowed_code }}" {% if branch_code == allowed_code %}selected{% endif %}>{{ allowed_code }}</option>
  {% endfor %}
</select>
```

- [ ] **Step 4: Run the portal tests**

Run: `py -3 -m pytest tests/test_sync_admin_client_portal.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sync-admin/app/web/routes/pages.py sync-admin/app/templates/client_reports.html sync-admin/app/templates/client_dashboard.html tests/test_sync_admin_client_portal.py
git commit -m "feat: aplica escopo por filial no portal cliente"
```

### Task 5: Add admin UI for client scope and branch permissions

**Files:**
- Modify: `sync-admin/app/templates/settings.html`
- Modify: `sync-admin/app/web/routes/pages.py`
- Modify: `tests/test_sync_admin_settings_client_scope.py`

- [ ] **Step 1: Write the failing UI integration test**

```python
def test_settings_page_accepts_client_scope_and_branch_selection(monkeypatch):
    _prepare_sync_admin("test_settings_scope_form.db")

    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(ControlService, "fetch_company_branch_options", lambda self, empresa_id: ["0001", "0002", "0003"])

    with TestClient(app) as client:
        login = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
        assert login.status_code in (302, 303)

        response = client.post(
            "/settings/users",
            data={
                "username": "cliente_matriz_filial",
                "full_name": "Cliente Matriz Filial",
                "password": "cliente123",
                "role": "client",
                "empresa_id": "55555555000155",
                "scope_type": "branch_set",
                "allowed_branch_codes": ["0001", "0003"],
            },
            follow_redirects=False,
        )

        assert response.status_code in (302, 303)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py::test_settings_page_accepts_client_scope_and_branch_selection -v`

Expected: FAIL because the form does not send scope fields yet.

- [ ] **Step 3: Update the settings form and route handler**

```html
<!-- sync-admin/app/templates/settings.html -->
<div class="col-md-2">
  <select class="form-select" name="scope_type">
    <option value="">sem escopo</option>
    <option value="company">empresa inteira</option>
    <option value="branch_set">filiais especificas</option>
  </select>
</div>
<div class="col-md-12">
  <label class="form-label">Filiais permitidas</label>
  <div class="d-flex gap-2 flex-wrap">
    <label class="form-check"><input class="form-check-input" type="checkbox" name="allowed_branch_codes" value="0001" />0001</label>
    <label class="form-check"><input class="form-check-input" type="checkbox" name="allowed_branch_codes" value="0002" />0002</label>
    <label class="form-check"><input class="form-check-input" type="checkbox" name="allowed_branch_codes" value="0003" />0003</label>
  </div>
</div>
```

```python
# sync-admin/app/web/routes/pages.py
@router.post("/settings/users")
def settings_create_user(
    ...,
    scope_type: str | None = Form(None),
    allowed_branch_codes: list[str] = Form(default_factory=list),
):
    service.create_user(
        UserCreateRequest(
            username=username,
            full_name=full_name,
            password=password,
            role=role,
            empresa_id=empresa_id,
            scope_type=scope_type,
            allowed_branch_codes=allowed_branch_codes,
        )
    )
```

- [ ] **Step 4: Run the settings tests**

Run: `py -3 -m pytest tests/test_sync_admin_settings_client_scope.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sync-admin/app/templates/settings.html sync-admin/app/web/routes/pages.py tests/test_sync_admin_settings_client_scope.py
git commit -m "feat: adiciona gestao de escopo do cliente no painel admin"
```

### Task 6: Enrich connected APIs with company identification and admin navigation

**Files:**
- Modify: `sync-admin/app/templates/connected_apis.html`
- Modify: `sync-admin/app/templates/connected_api_detail.html`
- Modify: `sync-admin/app/web/routes/pages.py`
- Test: `tests/test_sync_admin_connected_apis.py`

- [ ] **Step 1: Write the failing admin page test**

```python
def test_connected_apis_page_shows_company_identity_and_report_link(monkeypatch):
    _prepare_sync_admin("test_connected_apis_company_identity.db")

    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(
        ControlService,
        "fetch_remote_clients",
        lambda self, **kwargs: [
            {
                "id": "client-1",
                "empresa_id": "12345678000199",
                "empresa_nome": "Empresa XPTO",
                "hostname": "api-loja-01",
                "status": "online",
                "last_sync_at": "2026-04-20T10:00:00Z",
                "last_command_poll_at": "2026-04-20T10:05:00Z",
            }
        ],
    )

    with TestClient(app) as client:
        ...
        response = client.get("/connected-apis")
        assert "12345678000199" in response.text
        assert "Empresa XPTO" in response.text
        assert "Abrir relatórios" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m pytest tests/test_sync_admin_connected_apis.py::test_connected_apis_page_shows_company_identity_and_report_link -v`

Expected: FAIL because the template does not render company identity and report navigation yet.

- [ ] **Step 3: Add the admin navigation link and improved labeling**

```html
<!-- sync-admin/app/templates/connected_apis.html -->
<thead>
  <tr>
    <th>CNPJ</th>
    <th>Empresa</th>
    <th>Hostname</th>
    <th>Status</th>
    <th>Ultimo sync</th>
    <th>Ultimo poll</th>
    <th>Acoes</th>
  </tr>
</thead>
...
<td><code>{{ client.empresa_id }}</code></td>
<td>{{ client.empresa_nome or "-" }}</td>
...
<td class="d-flex gap-2">
  <a class="btn btn-sm btn-outline-primary" href="/connected-apis/{{ client.id }}">Abrir</a>
  <a class="btn btn-sm btn-outline-secondary" href="/reports?empresa_id={{ client.empresa_id }}">Abrir relatorios</a>
</td>
```

- [ ] **Step 4: Run the connected API tests**

Run: `py -3 -m pytest tests/test_sync_admin_connected_apis.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sync-admin/app/templates/connected_apis.html sync-admin/app/templates/connected_api_detail.html sync-admin/app/web/routes/pages.py tests/test_sync_admin_connected_apis.py
git commit -m "feat: melhora identificacao e navegacao no painel de apis"
```

### Task 7: Final verification and memory updates

**Files:**
- Modify: `cerebro_vivo/estado_atual.md`
- Modify: `cerebro_vivo/memoria_projeto.json`

- [ ] **Step 1: Run the focused test suite**

Run:

```bash
py -3 -m pytest tests/test_sync_admin_client_scope.py tests/test_sync_admin_settings_client_scope.py tests/test_sync_admin_client_portal.py tests/test_sync_admin_connected_apis.py -q
```

Expected: all tests PASS

- [ ] **Step 2: Run the broader sync-admin smoke suite**

Run:

```bash
py -3 -m pytest tests/test_sync_admin_reports.py tests/test_sync_admin_rbac.py tests/test_sync_admin_health.py -q
```

Expected: all tests PASS with no regression in the admin/client portal.

- [ ] **Step 3: Update executive memory**

```markdown
## Atualizacao desta continuidade

- Escopo de cliente agora diferencia `company` e `branch_set`.
- Portal cliente respeita permissoes por filial com matriz `0001`.
- Painel admin ganhou gestao explicita de escopo e navegacao por CNPJ/empresa.
```

- [ ] **Step 4: Commit**

```bash
git add cerebro_vivo/estado_atual.md cerebro_vivo/memoria_projeto.json
git commit -m "docs: registra escopo de cliente por empresa e filial"
```

## Self-review

### Spec coverage

- Painel admin com papel operacional separado do cliente: coberto nas Tasks 5 e 6.
- Portal cliente sem acesso tecnico e sem seletor de empresa: coberto nas Tasks 3 e 4.
- Escopo `company` e `branch_set`: coberto nas Tasks 1, 2 e 3.
- Tabela relacional para filiais permitidas: coberto nas Tasks 1 e 2.
- Matriz `0001` e filiais `0002+`: coberto nas Tasks 3, 4 e 5.
- Navegacao do admin por CNPJ/empresa para abrir relatorios: coberto na Task 6.

### Placeholder scan

- Nenhum `TODO`, `TBD` ou referencia vaga ficou no plano.
- Todos os comandos de teste estao explicitos.
- Cada componente novo tem caminho exato.

### Type consistency

- `scope_type` padronizado como `company | branch_set`.
- `allowed_branch_codes` padronizado como lista de `str`.
- `user_branch_permissions` padronizada com `user_id`, `empresa_id`, `branch_code`, `can_view_reports`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-20-client-access-scope.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
