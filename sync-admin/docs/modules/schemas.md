# Schemas

## Description
Defines request and response contracts for API and web-facing operations.

## Structure
- `app/schemas/auth.py`
- `app/schemas/sync.py`
- `app/schemas/users.py`
- `app/schemas/__init__.py`

## Integrations
- FastAPI request validation
- Pydantic models
- API routes and form handlers
- User and sync services

## Flow
1. Incoming requests are parsed into schema objects.
2. Validation enforces payload shape, field length, and type constraints.
3. Services consume validated data and return response models.

## Critical Points
- Keep validation rules explicit and close to the interface contract.
- Reject malformed sync payloads before they reach the service layer.
- Keep user creation constraints aligned with the allowed role set.

## Tests
- Validate through API integration tests and form submission flows.
- Confirm invalid payloads fail at the schema boundary.
