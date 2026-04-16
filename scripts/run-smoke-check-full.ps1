$ErrorActionPreference = "Stop"

$root = (Resolve-Path ".").Path
$rePath = "E:\Projetos\ENGENHARIA_REVERSA\XDSoftware-Reverse-Engineering"

if (-not (Test-Path -LiteralPath $rePath)) { throw "Fonte nao encontrada: $rePath" }

if (-not (Test-Path -LiteralPath ".env")) {
  Copy-Item -LiteralPath ".env.example" -Destination ".env"
}

# Full mode: no ingestion cap.
docker run --rm `
  -v "${root}:/workspace" `
  -v "${rePath}:/knowledge/re:ro" `
  -w /workspace `
  -e KNOWLEDGE_SOURCE_PATHS="/knowledge/re" `
  -e DB_PATH="output/system.db" `
  -e OBSIDIAN_VAULT_PATH="obsidian-vault" `
  -e NEXUS_MANIFEST_PATH="nexus-manifests" `
  -e JWT_SECRET="smoke-secret" `
  -e JWT_ALGORITHM="HS256" `
  -e JWT_ACCESS_EXPIRES_MINUTES="60" `
  -e JWT_REFRESH_EXPIRES_MINUTES="120" `
  -e AUTH_USERS="admin:admin123:admin;viewer:viewer123:viewer" `
  -e MAX_FILES_PER_SOURCE="0" `
  -e FAST_FILE_FINGERPRINT="1" `
  python:3.12-slim `
  sh -lc "pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir httpx && PYTHONPATH=packages/shared/src python scripts/smoke_check.py"
