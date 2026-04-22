# API

## Description
Handles the machine-facing HTTP surface for health checks and synchronization ingestion.

## Structure
- `app/api/routes/health_api.py`
- `app/api/routes/sync_api.py`
- `app/api/routes/__init__.py`
- `app/api/__init__.py`

## Integrations
- `app.core.db.get_db`
- `app.schemas.sync.SyncPayloadIn`
- `app.services.sync_service.SyncService`
- `fastapi.APIRouter`
- `fastapi.Header`
- `fastapi.HTTPException`

## Flow
1. Expose `GET /health` for liveness checks.
2. Expose `POST /api/sync-data` for batch ingestion.
3. Require `X-API-Key` on sync requests.
4. Authenticate the integration key through the service layer.
5. Serialize the payload into persistence-friendly records and return the batch result.

## Critical Points
- Treat `X-API-Key` as mandatory for sync.
- Reject unauthorized requests with `401`.
- Keep request validation in schemas, not in route handlers.
- Log failures without leaking sensitive payload contents.
- Return a single batch response per request; do not process records one by one.

## Tests
- Health endpoint smoke check.
- Integration test covering successful sync, invalid API key, and payload validation.
