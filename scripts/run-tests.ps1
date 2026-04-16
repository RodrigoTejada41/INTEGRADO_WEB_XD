$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path

# Run tests in isolated Python container to avoid local interpreter issues.
docker run --rm `
  -v "${root}:/workspace" `
  -w /workspace `
  python:3.12-slim `
  sh -lc "pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir httpx && PYTHONPATH=packages/shared/src pytest -q"
