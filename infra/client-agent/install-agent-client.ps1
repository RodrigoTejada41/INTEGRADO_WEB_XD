param(
    [string]$InstallDir = "C:\MoviSyncAgent"
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
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Step "Copiando arquivos da aplicacao"
Copy-Item -Path $sourceAgent -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceBackend -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceRequirements -Destination $InstallDir -Force

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
else {
    $envText = Get-Content ".env" -Raw
    if ($envText -match "(?im)^AGENT_SOURCE_QUERY=.*salesdocumentsreportview" -and $envText -notmatch "(?im)^AGENT_SOURCE_QUERY=.*familia_produto" -and $envText -notmatch "(?im)^AGENT_SOURCE_QUERY=.*codigo_produto_local") {
        Write-Step "Atualizando AGENT_SOURCE_QUERY legado para autodeteccao"
        $envText = $envText -replace "(?im)^AGENT_SOURCE_QUERY=.*$", "AGENT_SOURCE_QUERY=auto"
        Set-Content -Path ".env" -Value $envText -Encoding ascii
    }
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
".\.venv\Scripts\python.exe" -m agent_local.pairing_ui
'@ | Set-Content -Path "Abrir_Painel_Local.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
".\.venv\Scripts\python.exe" -m agent_local.main
'@ | Set-Content -Path "Iniciar_Agente.cmd" -Encoding ascii

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
Write-Host "2) Execute: $InstallDir\Abrir_Painel_Local.cmd"
Write-Host "3) Depois execute: $InstallDir\Iniciar_Agente.cmd"

