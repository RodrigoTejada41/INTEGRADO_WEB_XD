param(
    [string]$InstallDir = "C:\MoviSyncAgent",
    [switch]$ForceReinstall
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[instalador] $Message"
}

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceAgent = Join-Path $packageRoot "agent_local"
$sourceBackend = Join-Path $packageRoot "backend"
$sourceRequirements = Join-Path $packageRoot "requirements.txt"

if (!(Test-Path $sourceAgent) -or !(Test-Path $sourceBackend) -or !(Test-Path $sourceRequirements)) {
    throw "Pacote invalido. Esperado: agent_local/, backend/ e requirements.txt ao lado do instalador."
}

Write-Step "Preparando pasta de instalacao em $InstallDir"
if ($ForceReinstall -and (Test-Path $InstallDir)) {
    Write-Step "ForceReinstall ativo: limpando instalacao anterior"
    Remove-Item -Path $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Step "Copiando arquivos da aplicacao"
Copy-Item -Path $sourceAgent -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceBackend -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceRequirements -Destination $InstallDir -Force

$sourceManifest = Join-Path $packageRoot "release-manifest.txt"
if (Test-Path $sourceManifest) {
    Copy-Item -Path $sourceManifest -Destination (Join-Path $InstallDir "release-manifest.txt") -Force
} else {
    @(
        "version=dev-local"
        "created_at=$(Get-Date -Format s)"
        "source_repo=unknown"
    ) | Set-Content -Path (Join-Path $InstallDir "release-manifest.txt") -Encoding ascii
}

if (Test-Path (Join-Path $packageRoot "scripts")) {
    Copy-Item -Path (Join-Path $packageRoot "scripts") -Destination $InstallDir -Recurse -Force
}

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $pythonCmd) {
    throw "Python launcher (py) nao encontrado. Instale Python 3.11+ antes."
}

Write-Step "Criando virtualenv"
Push-Location $InstallDir
py -3 -m venv .venv

Write-Step "Instalando dependencias"
& "$InstallDir\.venv\Scripts\python.exe" -m pip install --upgrade pip
& "$InstallDir\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if (!(Test-Path ".env")) {
    Write-Step "Criando .env inicial a partir de agent_local/.env.example"
    Copy-Item "agent_local\.env.example" ".env"
}

Write-Step "Criando atalhos cmd"
@'
@echo off
cd /d %~dp0
".\.venv\Scripts\python.exe" -m agent_local.pairing_ui
'@ | Set-Content -Path "Abrir_Vinculacao.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
if not exist ".\agent_local\data\agent_api_key.txt" (
  echo [agente] API key local nao encontrada em agent_local\data\agent_api_key.txt
  echo [agente] Execute primeiro: Abrir_Vinculacao.cmd
  pause
  exit /b 1
)
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\agent-sync.log"
echo [agente] iniciando... >> "%LOG_FILE%"
".\.venv\Scripts\python.exe" -m agent_local.main >> "%LOG_FILE%" 2>&1
echo.
echo [agente] processo encerrado. Verifique o log:
echo %LOG_FILE%
pause
'@ | Set-Content -Path "Iniciar_Agente.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\agent-sync-debug.log"
echo [agente-debug] iniciando em modo foreground...
".\.venv\Scripts\python.exe" -m agent_local.main 1>> "%LOG_FILE%" 2>&1
echo.
echo [agente-debug] finalizado. Ultimas linhas do log:
powershell -NoProfile -Command "if (Test-Path '%LOG_FILE%') { Get-Content -Path '%LOG_FILE%' -Tail 80 }"
pause
'@ | Set-Content -Path "Iniciar_Agente_Debug.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File ".\scripts\set-agent-manual-password.ps1" -Password 25032015
pause
'@ | Set-Content -Path "Definir_Senha_Manual.cmd" -Encoding ascii

Pop-Location

Write-Step "Instalacao concluida."
Write-Host ""
Write-Host "Proximos passos:"
Write-Host "1) Execute: $InstallDir\Definir_Senha_Manual.cmd"
Write-Host "2) Execute: $InstallDir\Abrir_Vinculacao.cmd"
Write-Host "3) Depois execute: $InstallDir\Iniciar_Agente.cmd"
Write-Host "4) Se falhar, execute: $InstallDir\Iniciar_Agente_Debug.cmd"

