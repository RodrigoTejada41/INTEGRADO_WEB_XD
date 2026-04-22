# Repositories

## Description
Encapsulates persistence operations and query composition for users, integration keys, batches, and records.

## Structure
- `app/repositories/user_repository.py`
- `app/repositories/integration_repository.py`
- `app/repositories/sync_repository.py`
- `app/repositories/__init__.py`

## Integrations
- SQLAlchemy sessions
- Domain models
- Service layer orchestration

## Flow
1. Services request persistence operations from repositories.
2. Repositories translate use cases into SQLAlchemy queries or mutations.
3. The repository commits or flushes changes when the use case requires persistence.
4. Query results are returned to services in domain-friendly form.

## Critical Points
- Keep query logic isolated from routes and templates.
- Use explicit ordering and pagination for list operations.
- Preserve commit boundaries so that higher layers can reason about state transitions.
- Do not leak ORM details into the web layer.

## Tests
- Validate batch creation, record insertion, listing, and dashboard counts through integration coverage.
- Validate user and integration key lookups during authentication and login flows.
