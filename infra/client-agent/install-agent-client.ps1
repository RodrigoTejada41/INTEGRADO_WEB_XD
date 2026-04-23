param(
    [string]$InstallDir = "C:\MoviSyncAgent",
    [switch]$ForceReinstall
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[instalador] $Message"
}

function Stop-AgentProcesses([string]$TargetDir) {
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            ($_.Name -in @("python.exe", "pythonw.exe", "py.exe")) -and
            $_.CommandLine -and $_.CommandLine -like "*$TargetDir*"
        }

    foreach ($process in $processes) {
        Write-Step "Encerrando processo $($process.Name) (PID $($process.ProcessId))"
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Remove-DirectoryWithRetry([string]$TargetDir, [int]$RetryCount = 5) {
    Stop-AgentProcesses -TargetDir $TargetDir
    Start-Sleep -Seconds 2

    for ($attempt = 1; $attempt -le $RetryCount; $attempt++) {
        try {
            if (Test-Path $TargetDir) {
                Remove-Item -Path $TargetDir -Recurse -Force -ErrorAction Stop
            }
            return
        } catch {
            if ($attempt -eq $RetryCount) {
                throw
            }
            Write-Step "Falha ao remover $TargetDir. Tentativa $attempt de $RetryCount."
            Start-Sleep -Seconds 2
        }
    }
}

function Backup-PersistedState([string]$TargetDir) {
    $backupDir = Join-Path $env:TEMP ("MoviSyncAgentBackup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    $itemsToPreserve = @(
        ".env",
        "agent_local\data\agent_api_key.txt",
        "agent_local\data\local_client_identity.json",
        "agent_local\data\checkpoints.json"
    )

    foreach ($relativePath in $itemsToPreserve) {
        $sourcePath = Join-Path $TargetDir $relativePath
        if (!(Test-Path $sourcePath)) {
            continue
        }

        $destinationPath = Join-Path $backupDir $relativePath
        $destinationParent = Split-Path -Parent $destinationPath
        if ($destinationParent) {
            New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        }
        Copy-Item -Path $sourcePath -Destination $destinationPath -Force
    }

    return $backupDir
}

function Restore-PersistedState([string]$TargetDir, [string]$BackupDir) {
    if ([string]::IsNullOrWhiteSpace($BackupDir) -or !(Test-Path $BackupDir)) {
        return
    }

    $itemsToRestore = @(
        ".env",
        "agent_local\data\agent_api_key.txt",
        "agent_local\data\local_client_identity.json",
        "agent_local\data\checkpoints.json"
    )

    foreach ($relativePath in $itemsToRestore) {
        $sourcePath = Join-Path $BackupDir $relativePath
        if (!(Test-Path $sourcePath)) {
            continue
        }

        $destinationPath = Join-Path $TargetDir $relativePath
        $destinationParent = Split-Path -Parent $destinationPath
        if ($destinationParent) {
            New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        }
        Copy-Item -Path $sourcePath -Destination $destinationPath -Force
    }
}

function Invoke-Checked([scriptblock]$Command, [string]$ErrorMessage) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceAgent = Join-Path $packageRoot "agent_local"
$sourceBackend = Join-Path $packageRoot "backend"
$sourceRequirements = Join-Path $packageRoot "requirements.txt"
$sourceClientRequirements = Join-Path $packageRoot "requirements-client.txt"

if (!(Test-Path $sourceAgent) -or !(Test-Path $sourceBackend) -or !(Test-Path $sourceRequirements)) {
    throw "Pacote invalido. Esperado: agent_local/, backend/ e requirements.txt ao lado do instalador."
}

Write-Step "Preparando pasta de instalacao em $InstallDir"
$persistedStateBackup = $null
if ($ForceReinstall -and (Test-Path $InstallDir)) {
    Write-Step "ForceReinstall ativo: limpando instalacao anterior"
    $persistedStateBackup = Backup-PersistedState -TargetDir $InstallDir
    Remove-DirectoryWithRetry -TargetDir $InstallDir
}
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Step "Copiando arquivos da aplicacao"
Copy-Item -Path $sourceAgent -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceBackend -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceRequirements -Destination $InstallDir -Force
if (Test-Path $sourceClientRequirements) {
    Copy-Item -Path $sourceClientRequirements -Destination (Join-Path $InstallDir "requirements-client.txt") -Force
}

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

Restore-PersistedState -TargetDir $InstallDir -BackupDir $persistedStateBackup

$pythonCmd = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $pythonCmd) {
    throw "Python launcher (py) nao encontrado. Instale Python 3.11+ antes."
}

Write-Step "Criando virtualenv"
Push-Location $InstallDir
Invoke-Checked { py -3 -m venv .venv } "Falha ao criar virtualenv."

Write-Step "Instalando dependencias"
Invoke-Checked { & "$InstallDir\.venv\Scripts\python.exe" -m pip install --upgrade pip } "Falha ao atualizar pip."
if (Test-Path (Join-Path $InstallDir "requirements-client.txt")) {
    Invoke-Checked { & "$InstallDir\.venv\Scripts\python.exe" -m pip install -r requirements-client.txt } "Falha ao instalar requirements-client.txt."
} else {
    Invoke-Checked { & "$InstallDir\.venv\Scripts\python.exe" -m pip install -r requirements.txt } "Falha ao instalar requirements.txt."
}

if (!(Test-Path ".env")) {
    Write-Step "Criando .env inicial a partir de agent_local/.env.example"
    Copy-Item "agent_local\.env.example" ".env"
}

Write-Step "Criando atalhos cmd"
@'
@echo off
cd /d %~dp0
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\pairing-ui.log"
set "PYTHON=.\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo.
  echo [vinculacao] Python local nao encontrado.
  echo [vinculacao] Execute novamente a instalacao.
  pause
  exit /b 1
)
"%PYTHON%" -c "import agent_local.pairing_ui" 1>> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo.
  echo [vinculacao] Interface grafica indisponivel.
  echo [vinculacao] Veja o log: %LOG_FILE%
  echo [vinculacao] Abrindo fallback em terminal.
  "%PYTHON%" -m agent_local.pairing_cli
  if errorlevel 1 (
    echo.
    echo [vinculacao] Falha no fallback terminal.
    pause
    exit /b 1
  )
  exit /b 0
)
"%PYTHON%" -m agent_local.pairing_ui 1>> "%LOG_FILE%" 2>&1
if errorlevel 1 (
  echo.
  echo [vinculacao] Falha ao abrir interface grafica.
  echo [vinculacao] Veja o log: %LOG_FILE%
  echo [vinculacao] Abrindo fallback em terminal.
  "%PYTHON%" -m agent_local.pairing_cli
  if errorlevel 1 (
    echo.
    echo [vinculacao] Falha no fallback terminal.
    pause
    exit /b 1
  )
)
'@ | Set-Content -Path "Abrir_Vinculacao.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
".\.venv\Scripts\python.exe" -m agent_local.pairing_cli
if errorlevel 1 (
  echo.
  echo [vinculacao-cli] Falha na vinculacao.
  pause
  exit /b 1
)
echo.
echo [vinculacao-cli] Concluido.
pause
'@ | Set-Content -Path "Abrir_Vinculacao_CLI.cmd" -Encoding ascii

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
set "PYTHON=.\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo [agente] Python local nao encontrado em .\.venv\Scripts\python.exe
  pause
  exit /b 1
)
set "VBS_FILE=%~dp0Iniciar_Agente.vbs"
if not exist "%VBS_FILE%" (
  echo [agente] Launcher oculto nao encontrado.
  pause
  exit /b 1
)
wscript //nologo "%VBS_FILE%"
exit /b 0
'@ | Set-Content -Path "Iniciar_Agente.cmd" -Encoding ascii

@"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run "cmd /c ""$InstallDir\.venv\Scripts\python.exe -m agent_local.main >> $InstallDir\logs\agent-sync.log 2>&1""", 0, False
"@ | Set-Content -Path "Iniciar_Agente.vbs" -Encoding ascii

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
Write-Host "   (fallback terminal: $InstallDir\Abrir_Vinculacao_CLI.cmd)"
Write-Host "3) Depois execute: $InstallDir\Iniciar_Agente.cmd"
Write-Host "4) Se falhar, execute: $InstallDir\Iniciar_Agente_Debug.cmd"

