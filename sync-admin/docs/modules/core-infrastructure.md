# Core Infrastructure

## Description
Provides shared infrastructure for database access, logging configuration, and security primitives.

## Structure
- `app/core/db.py`
- `app/core/logging.py`
- `app/core/security.py`
- `app/core/__init__.py`

## Integrations
- SQLAlchemy engine and session factory
- Logging subsystem
- Password hashing with `passlib`
- JWT token encoding and verification
- Integration key hashing

## Flow
1. Build the SQLAlchemy engine from the configured database URL.
2. Expose a shared session factory for repositories and routes.
3. Configure structured application logging.
4. Hash and verify passwords and integration keys through security helpers.

## Critical Points
- Keep the database session lifecycle short and explicit.
- Use one hashing strategy per secret type.
- Preserve JWT secret ownership in configuration, not in code.
- Maintain SQLite compatibility for local development.

## Tests
- Validate repository operations through integration tests that exercise the session factory.
- Validate token and password helpers through auth and login flows.
