# Services

## Description
Implements application use cases and orchestrates repositories, security helpers, file outputs, and control-plane calls.

## Structure
- `app/services/auth_service.py`
- `app/services/control_service.py`
- `app/services/dashboard_service.py`
- `app/services/export_service.py`
- `app/services/sync_service.py`
- `app/services/user_service.py`
- `app/services/__init__.py`

## Integrations
- `app.core.security`
- `app.repositories.user_repository`
- `app.repositories.sync_repository`
- `app.repositories.integration_repository`
- `app.schemas.users`
- `httpx`
- `pathlib.Path`
- CSV generation utilities

## Flow
1. Authentication service seeds and validates the admin user.
2. Sync service authenticates integration keys and ingests payloads into batches and records.
3. Dashboard service aggregates counts and time series data from repositories.
4. Control service talks to the API control plane, file-based agent key storage, and audit logs.
5. User service validates roles and creates panel users.
6. Export service converts structured rows into CSV outputs.

## Critical Points
- Keep business rules in services, not in routes or repositories.
- Hash passwords and API keys before persistence.
- Limit file system writes to clearly owned paths.
- Handle external HTTP failures gracefully in control-plane functions.
- Keep role validation deterministic and explicit.

## Tests
- Validate login and user bootstrap flows.
- Validate sync ingestion and dashboard summaries.
- Validate CSV export shape and content.
- Validate control-plane fallbacks when the remote API is unavailable.
