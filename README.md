# INTEGRADO WEB XD - Reverse Engineering Knowledge Pipeline

This project is a modular, non-monolithic pipeline that consumes reverse engineering knowledge files and turns them into structured, versioned data exposed by API.

## Main source path (processed by pipeline)
The ingestion source is configured in `.env`:
- `E:\Projetos\ENGENHARIA_REVERSA\XDSoftware-Reverse-Engineering`

Use `KNOWLEDGE_SOURCE_PATHS` to change the processing source folder.

## External knowledge reference (not processed)
`CEREBRO_VIVO` must be used only for consultation, not ingestion.
Use `KNOWLEDGE_REFERENCE_PATHS` only as reference metadata.

## Modules
- `apps/ingestion-service`: monitors source folders, indexes files, creates ingestion events
- `apps/reverse-engineering-service`: interprets files and infers structure
- `apps/transformation-service`: normalizes interpreted data and creates dataset versions
- `apps/persistence-service`: writes evidence to Obsidian vault and Nexus manifest folders
- `apps/api-service`: JWT-secured RBAC API for files, jobs, datasets and reports
- `packages/shared`: shared config, sqlite persistence, event queue, and adapters

## Run locally
1. Create virtualenv and install dependencies:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Copy env file:
```powershell
Copy-Item .env.example .env
```

## Quick execution (single batch)
```powershell
.\scripts\run-pipeline-once.ps1
```
This executes ingestion and drains all pending events through reverse engineering, transformation and persistence.

## Continuous execution
```powershell
.\scripts\start-services.ps1
```
This opens 5 terminals and starts all services including API.

## JWT auth, refresh and RBAC
1. Login and receive `access_token` + `refresh_token`:
```http
POST /auth/token
{
  "username": "admin",
  "password": "admin123"
}
```
2. Refresh (rotates refresh token and invalidates old one):
```http
POST /auth/refresh
{
  "refresh_token": "<refresh_token>"
}
```
3. Logout (revokes current access token and optional refresh token):
```http
POST /auth/logout
Authorization: Bearer <access_token>
{
  "refresh_token": "<refresh_token_optional>"
}
```
4. Use access token on protected endpoints:
```http
Authorization: Bearer <access_token>
```
5. Roles:
- `admin`: files/jobs/datasets/reports/audit
- `analyst`: files/jobs/datasets/reports
- `viewer`: datasets/reports

## API checks
- `GET /health`
- `POST /auth/token`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/files`
- `GET /api/v1/jobs`
- `GET /api/v1/datasets`
- `GET /api/v1/reports/summary`
- `GET /api/v1/audit-events` (admin only)

## Data flow
`source files -> ingestion -> reverse engineering -> transformation -> DB -> Nexus manifests + Obsidian notes -> API reports`

## Notes
- Storage is SQLite for local development speed (`output/system.db`).
- The architecture is modular and can be migrated to PostgreSQL + message broker without changing service boundaries.
- Obsidian data is generated as Markdown in `obsidian-vault`.
- Nexus integration is represented by versioned manifest artifacts in `nexus-manifests`.

## Automated tests
Run the test suite in Docker:
```powershell
.\scripts\run-tests.ps1
```

Current automated coverage:
- health endpoint
- login + `/api/v1/auth/me`
- RBAC enforcement (viewer denied on `/api/v1/files`)
- refresh token rotation (old refresh rejected)
- logout revocation (access token invalid after logout)

## End-to-end smoke check
Run fast smoke (capped ingestion):
```powershell
.\scripts\run-smoke-check.ps1
```

Run full smoke (no ingestion cap):
```powershell
.\scripts\run-smoke-check-full.ps1
```

This validates:
- ingestion from `ENGENHARIA_REVERSA`
- reverse engineering + transformation + persistence
- generated artifacts in Obsidian and Nexus manifest folders
- JWT login and protected API endpoints
