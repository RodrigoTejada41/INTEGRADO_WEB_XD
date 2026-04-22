# Web UI

## Description
Provides the browser-facing interface, including page routes, session access control, templates, and static assets.

## Structure
- `app/web/deps.py`
- `app/web/routes/pages.py`
- `app/web/__init__.py`
- `app/templates/base.html`
- `app/templates/dashboard.html`
- `app/templates/history.html`
- `app/templates/login.html`
- `app/templates/records.html`
- `app/templates/settings.html`
- `app/templates/partials/`
- `app/static/css/app.css`
- `app/static/js/dashboard.js`

## Integrations
- `app.services.auth_service`
- `app.services.control_service`
- `app.services.dashboard_service`
- `app.services.export_service`
- `app.services.user_service`
- `app.repositories.sync_repository`
- `app.repositories.user_repository`
- Session middleware
- Jinja2 templates
- Static asset serving

## Flow
1. Unauthenticated users are redirected to `/login`.
2. Session-backed users are authorized by role.
3. Dashboard, records, history, and settings pages render server-side.
4. JavaScript fetches `/dashboard/data` to refresh the dashboard state.
5. Forms submit to web routes that call services and redirect back with feedback.

## Critical Points
- Keep the browser-facing auth flow session-based and explicit.
- Enforce role checks in dependency functions, not in templates.
- Keep the UI responsive without embedding business logic in templates.
- Preserve local-first paths for file-backed control operations.

## Tests
- Validate login redirect, dashboard access, records access, and settings permissions.
- Validate browser flows through integration tests and manual smoke checks.
