# Configuration

## Description
Centralizes runtime settings loaded from environment variables and `.env`.

## Structure
- `app/config/settings.py`
- `app/config/__init__.py`
- `.env`
- `.env.example`
- `VERSION`

## Integrations
- `app.main`
- `app.core.db`
- `app.core.logging`
- `app.services.control_service`
- `app.services.sync_service`

## Flow
1. Load environment variables from `.env`.
2. Resolve application identity, database URL, secrets, and operational defaults.
3. Share the settings object across bootstrap, services, and deployment routines.

## Critical Points
- Keep sensitive values outside source control.
- Make defaults explicit and safe for local development.
- Avoid scattering hardcoded hostnames, secrets, and file paths.
- Keep local-first paths configurable through settings.

## Tests
- Validate startup with `.env.example` values.
- Confirm the app can boot with SQLite locally and PostgreSQL in containerized deployments.
