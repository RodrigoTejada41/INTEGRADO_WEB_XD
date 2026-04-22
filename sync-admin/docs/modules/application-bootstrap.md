# Application Bootstrap

## Description
Bootstraps the FastAPI application, initializes database state, configures middleware, and wires the API and web routers.

## Structure
- `app/main.py`
- `app/__init__.py`

## Integrations
- `app.config.settings`
- `app.core.db`
- `app.core.logging`
- `app.models`
- `app.services.auth_service`
- `app.services.sync_service`
- `app.api.routes.health_api`
- `app.api.routes.sync_api`
- `app.web.routes.pages`
- FastAPI lifespan hooks
- Session middleware
- CORS middleware
- Static file mounting

## Flow
1. Load settings and configure logging.
2. Create tables during application lifespan.
3. Seed the initial admin user and default integration key.
4. Register middleware, static assets, and routers.
5. Serve requests through the API and web layers.

## Critical Points
- Keep startup logic thin and deterministic.
- Avoid import cycles between bootstrap, services, and repositories.
- Use environment-driven secrets and bootstrap data.
- Keep the lifespan side effects limited to schema creation and initial seeding.

## Tests
- Validate through repository-level integration tests and application startup smoke checks.
- Confirm health endpoint availability after startup.
