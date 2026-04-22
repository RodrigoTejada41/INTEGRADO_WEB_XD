# Database and Models

## Description
Defines the persistent domain entities and the relationships used by the sync-admin backend.

## Structure
- `app/models/user.py`
- `app/models/integration_key.py`
- `app/models/sync_batch.py`
- `app/models/sync_record.py`
- `app/models/__init__.py`

## Integrations
- `app.core.db.Base`
- SQLAlchemy ORM relationships
- Repository layer queries and persistence

## Flow
1. `users` stores administrative identities and roles.
2. `integration_keys` stores hashed API keys and usage metadata.
3. `sync_batches` captures batch-level ingestion metadata.
4. `sync_records` stores the record-level payloads linked to each batch.
5. Repositories load and persist these models through SQLAlchemy sessions.

## Critical Points
- Keep indexes on authentication and query-heavy fields.
- Store only hashed secrets.
- Preserve the batch-to-record relationship with delete-orphan semantics.
- Keep timestamps in UTC.

## Tests
- Validate through repository-level persistence tests and end-to-end sync flows.
- Confirm that model relationships cascade correctly when batches are managed.
