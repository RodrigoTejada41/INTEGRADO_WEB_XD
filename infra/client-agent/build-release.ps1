param(
    [string]$VersionTag = "",
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[release] $Message"
}

$clientRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $clientRoot)

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $clientRoot "releases"
}

if ([string]::IsNullOrWhiteSpace($VersionTag)) {
    $VersionTag = "v" + (Get-Date -Format "yyyy-MM-dd_HHmm")
}

$releaseDir = Join-Path $OutputRoot $VersionTag
if (Test-Path $releaseDir) {
    throw "Diretorio de release ja existe: $releaseDir"
}

Write-Step "Criando release em $releaseDir"
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Write-Step "Copiando instalador"
Copy-Item -Path (Join-Path $clientRoot "install-agent-client.ps1") -Destination $releaseDir -Force
Copy-Item -Path (Join-Path $clientRoot "Setup_Instalar_Cliente.bat") -Destination $releaseDir -Force
Copy-Item -Path (Join-Path $clientRoot "README.md") -Destination $releaseDir -Force

Write-Step "Copiando scripts do pacote"
Copy-Item -Path (Join-Path $clientRoot "scripts") -Destination $releaseDir -Recurse -Force

Write-Step "Copiando runtime do agente"
Copy-Item -Path (Join-Path $repoRoot "agent_local") -Destination $releaseDir -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "backend") -Destination $releaseDir -Recurse -Force
Copy-Item -Path (Join-Path $repoRoot "requirements.txt") -Destination $releaseDir -Force

Write-Step "Limpando arquivos temporarios de runtime"
Get-ChildItem -Path $releaseDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $releaseDir -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

$manifestPath = Join-Path $releaseDir "release-manifest.txt"
@(
    "version=$VersionTag"
    "created_at=$(Get-Date -Format s)"
    "source_repo=$repoRoot"
    "contents=install-agent-client.ps1,Setup_Instalar_Cliente.bat,README.md,scripts/,agent_local/,backend/,requirements.txt"
) | Set-Content -Path $manifestPath -Encoding ascii

Write-Step "Release pronta."
Write-Host "Version: $VersionTag"
Write-Host "Path: $releaseDir"
