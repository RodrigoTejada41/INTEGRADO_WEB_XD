# Deployment and Operations

## Description
Documents the containerized runtime, local bootstrap script, reverse proxy, and operational runtime files.

## Structure
- `docker-compose.yml`
- `Dockerfile`
- `nginx/default.conf`
- `scripts/init_db.py`
- `requirements.txt`
- `VERSION`

## Integrations
- PostgreSQL container
- FastAPI application container
- Nginx reverse proxy
- Bootstrap script for local database initialization
- Environment variables from `.env`

## Flow
1. Build the API image from `Dockerfile`.
2. Start PostgreSQL, API, and web containers with Docker Compose.
3. Use Nginx as the public entrypoint for the browser.
4. Initialize the database with the bootstrap script when needed.
5. Keep runtime configuration externalized through the environment.

## Critical Points
- Always keep secrets out of the image.
- Keep the API container dependent on database readiness.
- Expose only the web proxy to the host in normal operation.
- Ensure the `runtime` volume is mounted consistently when used.

## Tests
- Validate the stack with `docker compose up` and a health check.
- Confirm the browser reaches the web container and the API remains reachable through Nginx.
