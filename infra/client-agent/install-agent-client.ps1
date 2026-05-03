param(
    [string]$InstallDir = "C:\Movi_commanda",
    [switch]$OpenPanel,
    [switch]$OpenOrders
)

$ErrorActionPreference = "Stop"
$LegacyInstallDirs = @("C:\MoviSyncAgent")
$StateRelativePaths = @(
    ".env",
    "agent_local\data\agent_api_key.txt",
    "agent_local\data\local_api_token.txt",
    "agent_local\data\checkpoints.json",
    "agent_local\data\local_orders.db"
)

function Write-Step([string]$Message) {
    Write-Host "[instalador] $Message"
}

function Resolve-FullPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path).TrimEnd("\")
}

function Stop-MoviProcesses([string[]]$InstallDirs) {
    $resolvedDirs = $InstallDirs |
        Where-Object { ![string]::IsNullOrWhiteSpace($_) } |
        ForEach-Object { Resolve-FullPath $_ }

    if ($resolvedDirs.Count -eq 0) {
        return
    }

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = $_.CommandLine
            if ([string]::IsNullOrWhiteSpace($commandLine)) {
                return $false
            }
            foreach ($dir in $resolvedDirs) {
                if ($commandLine -like "*$dir*") {
                    return $true
                }
            }
            return $false
        } |
        ForEach-Object {
            try {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
            catch {
                Write-Step "Nao foi possivel parar processo antigo PID=$($_.ProcessId): $($_.Exception.Message)"
            }
        }
}

function Backup-InstallState([string[]]$InstallDirs, [string]$BackupRoot) {
    foreach ($installDir in $InstallDirs) {
        if ([string]::IsNullOrWhiteSpace($installDir) -or !(Test-Path $installDir)) {
            continue
        }
        foreach ($relativePath in $StateRelativePaths) {
            $source = Join-Path $installDir $relativePath
            if (!(Test-Path $source)) {
                continue
            }
            $destination = Join-Path $BackupRoot $relativePath
            $destinationDir = Split-Path -Parent $destination
            New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
            Copy-Item -Path $source -Destination $destination -Force
        }
    }
}

function Restore-InstallState([string]$BackupRoot, [string]$InstallDir) {
    if (!(Test-Path $BackupRoot)) {
        return
    }
    foreach ($relativePath in $StateRelativePaths) {
        $source = Join-Path $BackupRoot $relativePath
        if (!(Test-Path $source)) {
            continue
        }
        $destination = Join-Path $InstallDir $relativePath
        $destinationDir = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
        Copy-Item -Path $source -Destination $destination -Force
    }
}

function Remove-InstallTree([string]$InstallDir) {
    if ([string]::IsNullOrWhiteSpace($InstallDir) -or !(Test-Path $InstallDir)) {
        return
    }

    $resolved = Resolve-FullPath $InstallDir
    $hasInstallMarker = Test-Path (Join-Path $resolved "VERSAO_INSTALADA.txt")
    $hasAgentRuntime = (Test-Path (Join-Path $resolved "agent_local")) -and (Test-Path (Join-Path $resolved "backend"))
    $isKnownMoviPath = $resolved -match "^[A-Za-z]:\\Movi(SyncAgent|_commanda)$"

    if (!($hasInstallMarker -or $hasAgentRuntime -or $isKnownMoviPath)) {
        throw "Recusando remover pasta sem marcador de instalacao: $resolved"
    }

    Remove-Item -LiteralPath $resolved -Recurse -Force
}

function New-DesktopShortcut(
    [string]$Name,
    [string]$TargetPath,
    [string]$WorkingDirectory
) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        return
    }
    $shortcutPath = Join-Path $desktop $Name
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.Save()
}

function Remove-DesktopShortcutsByPrefix([string[]]$Prefixes) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        return
    }
    foreach ($prefix in $Prefixes) {
        Get-ChildItem -Path $desktop -Filter "$prefix*.lnk" -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
}

function New-StartupShortcut(
    [string]$Name,
    [string]$TargetPath,
    [string]$WorkingDirectory
) {
    $startup = [Environment]::GetFolderPath("Startup")
    if ([string]::IsNullOrWhiteSpace($startup)) {
        return
    }
    $shortcutPath = Join-Path $startup $Name
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.Save()
}

function Remove-StartupShortcutsByPrefix([string[]]$Prefixes) {
    $startup = [Environment]::GetFolderPath("Startup")
    if ([string]::IsNullOrWhiteSpace($startup)) {
        return
    }
    foreach ($prefix in $Prefixes) {
        Get-ChildItem -Path $startup -Filter "$prefix*.lnk" -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }
}

$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceAgent = Join-Path $packageRoot "agent_local"
$sourceBackend = Join-Path $packageRoot "backend"
$sourceRequirements = Join-Path $packageRoot "requirements.txt"
$packageVersionFile = Join-Path $packageRoot "package-version.txt"
$packageManifestFile = Join-Path $packageRoot "release-manifest.txt"
$packageVersion = "dev-local"
if (Test-Path $packageVersionFile) {
    $packageVersion = (Get-Content $packageVersionFile -Raw).Trim()
}
elseif (Test-Path $packageManifestFile) {
    $versionLine = Get-Content $packageManifestFile | Where-Object { $_ -like "version=*" } | Select-Object -First 1
    if ($versionLine) {
        $packageVersion = $versionLine.Substring("version=".Length).Trim()
    }
}

if (!(Test-Path $sourceAgent) -or !(Test-Path $sourceBackend) -or !(Test-Path $sourceRequirements)) {
    throw "Pacote invalido. Esperado: agent_local/, backend/ e requirements.txt ao lado do instalador."
}

$candidateInstallDirs = @($LegacyInstallDirs + @($InstallDir)) |
    ForEach-Object { Resolve-FullPath $_ } |
    Select-Object -Unique
$stateBackupRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("Movi_commanda_install_state_" + [System.Guid]::NewGuid().ToString("N"))

Write-Step "Parando processos antigos do aplicativo"
Stop-MoviProcesses $candidateInstallDirs

Write-Step "Preservando configuracao local e dados pendentes"
Backup-InstallState $candidateInstallDirs $stateBackupRoot

Write-Step "Removendo instalacoes antigas"
foreach ($candidateDir in $candidateInstallDirs) {
    Remove-InstallTree $candidateDir
}

Write-Step "Preparando pasta de instalacao em $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Step "Copiando arquivos da aplicacao"
Copy-Item -Path $sourceAgent -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceBackend -Destination $InstallDir -Recurse -Force
Copy-Item -Path $sourceRequirements -Destination $InstallDir -Force
Set-Content -Path (Join-Path $InstallDir "VERSAO_INSTALADA.txt") -Encoding ascii -Value @(
    "version=$packageVersion"
    "installed_at=$(Get-Date -Format s)"
)
if (Test-Path $packageManifestFile) {
    Copy-Item -Path $packageManifestFile -Destination (Join-Path $InstallDir "release-manifest.txt") -Force
}

if (Test-Path (Join-Path $packageRoot "scripts")) {
    Copy-Item -Path (Join-Path $packageRoot "scripts") -Destination $InstallDir -Recurse -Force
}

Write-Step "Restaurando configuracao local preservada"
Restore-InstallState $stateBackupRoot $InstallDir
Remove-Item -LiteralPath $stateBackupRoot -Recurse -Force -ErrorAction SilentlyContinue

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
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "agent_local\data") | Out-Null

$localApiTokenFile = Join-Path $InstallDir "agent_local\data\local_api_token.txt"
if (!(Test-Path $localApiTokenFile)) {
    $tokenBytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($tokenBytes)
    ($tokenBytes | ForEach-Object { $_.ToString("x2") }) -join "" |
        Set-Content -Path $localApiTokenFile -Encoding ascii
}

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
powershell -NoProfile -ExecutionPolicy Bypass -Command "$base='http://127.0.0.1:8765'; for ($i=0; $i -lt 12; $i++) { try { $health=Invoke-RestMethod -Uri ($base + '/health') -TimeoutSec 5; if ($health.status -eq 'ok') { Start-Process ($base + '/orders/ui'); exit 0 } } catch { Start-Sleep -Seconds 2 } }; Write-Host 'API local nao esta acessivel em http://127.0.0.1:8765. Inicie o Movi_commanda antes de abrir comandas.'; pause; exit 1"
'@ | Set-Content -Path "Abrir_Comandas_Locais.cmd" -Encoding ascii

$panelVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.pairing_ui", 0, False
"@
$panelVbsContent | Set-Content -Path "Abrir_Painel_Local.vbs" -Encoding ascii

$ordersVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\Abrir_Comandas_Locais.cmd" & """", 1, False
"@
$ordersVbsContent | Set-Content -Path "Abrir_Comandas_Locais.vbs" -Encoding ascii

@'
@echo off
cd /d %~dp0
wscript //nologo "%~dp0Abrir_Status_Sync.vbs"
'@ | Set-Content -Path "Iniciar_Agente.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
wscript //nologo "%~dp0Abrir_Status_Sync.vbs"
'@ | Set-Content -Path "Abrir_Status_Sync.cmd" -Encoding ascii

$statusVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.tray_app", 0, False
"@
$statusVbsContent | Set-Content -Path "Abrir_Status_Sync.vbs" -Encoding ascii

$localApiVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m uvicorn agent_local.local_api:app --host 127.0.0.1 --port 8765", 0, False
"@
$localApiVbsContent | Set-Content -Path "Abrir_API_Local.vbs" -Encoding ascii

$agentVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.main", 0, False
"@
$agentVbsContent | Set-Content -Path "Iniciar_Agente.vbs" -Encoding ascii

$windowsStartupVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.windows_autostart", 0, False
"@
$windowsStartupVbsContent | Set-Content -Path "Iniciar_Movi_commanda_Windows.vbs" -Encoding ascii

@'
@echo off
cd /d %~dp0
".\.venv\Scripts\python.exe" -m agent_local.main
pause
'@ | Set-Content -Path "Iniciar_Agente_Debug.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File ".\scripts\set-agent-manual-password.ps1" -Password 25032015
pause
'@ | Set-Content -Path "Definir_Senha_Manual.cmd" -Encoding ascii

if (Test-Path ".\scripts\set-agent-manual-password.ps1") {
    Write-Step "Configurando senha local de suporte"
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\set-agent-manual-password.ps1" -Password 25032015 | Out-Null
}

Write-Step "Criando atalhos na area de trabalho"
Remove-DesktopShortcutsByPrefix @(
    "Movi"
)
New-DesktopShortcut -Name "Movi_commanda Definicoes - $packageVersion.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Painel_Local.vbs") -WorkingDirectory $InstallDir
New-DesktopShortcut -Name "Movi_commanda Status - $packageVersion.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Status_Sync.vbs") -WorkingDirectory $InstallDir
New-DesktopShortcut -Name "Movi_commanda Iniciar Servico - $packageVersion.lnk" -TargetPath (Join-Path $InstallDir "Iniciar_Movi_commanda_Windows.vbs") -WorkingDirectory $InstallDir
New-DesktopShortcut -Name "Movi_commanda API Local - $packageVersion.lnk" -TargetPath (Join-Path $InstallDir "Abrir_API_Local.vbs") -WorkingDirectory $InstallDir
New-DesktopShortcut -Name "Movi_commanda - $packageVersion.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Comandas_Locais.vbs") -WorkingDirectory $InstallDir

Write-Step "Configurando inicializacao com Windows"
Remove-StartupShortcutsByPrefix @("Movi")
New-StartupShortcut -Name "Movi_commanda AutoStart.lnk" -TargetPath (Join-Path $InstallDir "Iniciar_Movi_commanda_Windows.vbs") -WorkingDirectory $InstallDir

Pop-Location

Write-Step "Instalacao concluida."
Write-Host ""
Write-Host "Versao instalada: $packageVersion"
Write-Host "Arquivo de versao: $InstallDir\VERSAO_INSTALADA.txt"
Write-Host ""
Write-Host "Proximos passos no painel local:"
Write-Host "1) Informe o codigo de vinculacao."
Write-Host "2) Configure o banco MariaDB local."
Write-Host "3) Clique para testar e salvar."
Write-Host "4) A API local, o Sync e o icone iniciam junto com o Windows."
Write-Host "5) Use o icone perto do relogio para iniciar, parar ou reiniciar."

if ($OpenPanel) {
    Write-Step "Abrindo painel local"
    Start-Process -FilePath "wscript.exe" -ArgumentList @("//nologo", (Join-Path $InstallDir "Abrir_Painel_Local.vbs")) -WorkingDirectory $InstallDir -WindowStyle Hidden
    Write-Step "Abrindo icone de status"
    Start-Process -FilePath "wscript.exe" -ArgumentList @("//nologo", (Join-Path $InstallDir "Iniciar_Movi_commanda_Windows.vbs")) -WorkingDirectory $InstallDir -WindowStyle Hidden
}
elseif ($OpenOrders) {
    Write-Step "Abrindo Movi_commanda"
    Start-Process -FilePath "wscript.exe" -ArgumentList @("//nologo", (Join-Path $InstallDir "Iniciar_Movi_commanda_Windows.vbs")) -WorkingDirectory $InstallDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Start-Process -FilePath "wscript.exe" -ArgumentList @("//nologo", (Join-Path $InstallDir "Abrir_Comandas_Locais.vbs")) -WorkingDirectory $InstallDir -WindowStyle Hidden
}

