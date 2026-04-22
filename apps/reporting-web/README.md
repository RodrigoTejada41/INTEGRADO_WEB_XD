# Reporting Web

## Description
Front-end module responsible for dashboards, dataset history, artifact visibility, and export-oriented views built on top of the API services.

## Structure
- `README.md`

## Integrations
- `apps/api-service`
- Dashboard and reporting endpoints
- Token-based authentication or gateway-based OAuth2
- Metric visualizations and export flows

## Flow
1. The user authenticates through the platform boundary.
2. The UI requests reporting and timeline data from the API.
3. The module renders operational views and history-focused pages.
4. Export actions surface curated data for operators and analysts.

## Critical Points
- Keep the module front-end only; do not embed backend business rules here.
- Keep dashboards navigable and lightweight.
- Treat API contracts as the source of truth.
- Preserve a local-first documentation entry for maintenance work.

## Tests
- Smoke test the report-loading pages.
- Validate API integration against the current reporting contract.
- Confirm export actions and timeline rendering.
