param(
    [string]$InstallDir = "C:\Movi_commanda",
    [switch]$OpenPanel,
    [switch]$OpenOrders
)

$ErrorActionPreference = "Stop"
$LegacyInstallDirs = @("C:\MoviSyncAgent")
$LocalApiPort = "8765"
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

function Invoke-CheckedCommand([string]$FilePath, [string[]]$Arguments, [string]$ErrorMessage) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$ErrorMessage Codigo de saida: $LASTEXITCODE"
    }
}

function Resolve-PythonLauncher() {
    $candidates = @("-3.12", "-3.11", "-3")
    foreach ($candidate in $candidates) {
        & py $candidate --version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $candidate
        }
    }
    throw "Python launcher (py) nao encontrou Python 3.11+. Instale Python 3.11 ou 3.12 antes."
}

function Resolve-LanIPv4() {
    try {
        $addresses = Get-NetIPConfiguration -ErrorAction Stop |
            Where-Object {
                $_.IPv4Address `
                    -and $_.NetAdapter.Status -eq "Up" `
                    -and $_.InterfaceAlias -notmatch "vEthernet|Virtual|VMware|VirtualBox|Docker|WSL|Loopback|Bluetooth" `
                    -and $_.IPv4Address.IPAddress -notlike "127.*" `
                    -and $_.IPv4Address.IPAddress -notlike "169.254.*"
            } |
            Sort-Object { if ($_.IPv4DefaultGateway) { 0 } else { 1 } } |
            ForEach-Object { $_.IPv4Address.IPAddress }
        if ($addresses) {
            return ($addresses | Select-Object -First 1)
        }
    }
    catch {
        return "IP-DA-MAQUINA"
    }
    return "IP-DA-MAQUINA"
}

function New-LocalPairingToken() {
    $alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    $bytes = New-Object byte[] 6
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $chars = foreach ($byte in $bytes) {
        $alphabet[$byte % $alphabet.Length]
    }
    return -join $chars
}

function Ensure-LocalApiFirewallRule([string]$Port) {
    try {
        $ruleName = "Movi_commanda API Local"
        $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        if ($existing) {
            Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Direction Inbound -Action Allow -Profile Private | Out-Null
            Set-NetFirewallPortFilter -AssociatedNetFirewallRule $existing -Protocol TCP -LocalPort $Port | Out-Null
            return
        }
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort $Port `
            -Profile Private | Out-Null
    }
    catch {
        Write-Step "Nao foi possivel configurar firewall automaticamente: $($_.Exception.Message)"
    }
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
            if ($_.ProcessId -eq $PID) {
                return
            }
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

function Remove-DesktopShortcutsByTargetRoots([string[]]$TargetRoots) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        return
    }
    $resolvedRoots = $TargetRoots |
        Where-Object { ![string]::IsNullOrWhiteSpace($_) } |
        ForEach-Object { Resolve-FullPath $_ }
    if ($resolvedRoots.Count -eq 0) {
        return
    }

    $shell = New-Object -ComObject WScript.Shell
    Get-ChildItem -Path $desktop -Filter "*.lnk" -ErrorAction SilentlyContinue |
        ForEach-Object {
            try {
                $shortcut = $shell.CreateShortcut($_.FullName)
                $target = $shortcut.TargetPath
                $workdir = $shortcut.WorkingDirectory
                foreach ($root in $resolvedRoots) {
                    if ($target -like "$root*" -or $workdir -like "$root*") {
                        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
                        return
                    }
                }
            }
            catch {
                Write-Step "Nao foi possivel inspecionar atalho $($_.FullName): $($_.Exception.Message)"
            }
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
$pythonVersionArg = Resolve-PythonLauncher

Write-Step "Criando virtualenv"
Push-Location $InstallDir
Invoke-CheckedCommand "py" @($pythonVersionArg, "-m", "venv", ".venv") "Falha ao criar virtualenv."

Write-Step "Instalando dependencias"
$venvPython = "$InstallDir\.venv\Scripts\python.exe"
Invoke-CheckedCommand $venvPython @("-m", "pip", "install", "--upgrade", "pip") "Falha ao atualizar pip."
Invoke-CheckedCommand $venvPython @("-m", "pip", "install", "-r", "requirements.txt") "Falha ao instalar dependencias."
Invoke-CheckedCommand $venvPython @("-c", "import fastapi, uvicorn, pydantic, pystray, PIL") "Dependencias obrigatorias nao foram instaladas."

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
$envText = Get-Content ".env" -Raw
if ($envText -notmatch "(?im)^LOCAL_ORDER_PUSH_XD_ENABLED=") {
    Add-Content -Path ".env" -Value "LOCAL_ORDER_PUSH_XD_ENABLED=true" -Encoding ascii
}
if ($envText -notmatch "(?im)^LOCAL_ORDER_XD_TERMINAL_ID=") {
    Add-Content -Path ".env" -Value "LOCAL_ORDER_XD_TERMINAL_ID=1" -Encoding ascii
}

Write-Step "Criando atalhos cmd"
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "agent_local\data") | Out-Null
$lanIPv4 = Resolve-LanIPv4

$localApiTokenFile = Join-Path $InstallDir "agent_local\data\local_api_token.txt"
if (!(Test-Path $localApiTokenFile)) {
    New-LocalPairingToken | Set-Content -Path $localApiTokenFile -Encoding ascii
}

Write-Step "Configurando firewall para acesso em rede local"
Ensure-LocalApiFirewallRule $LocalApiPort

Set-Content -Path (Join-Path $InstallDir "ACESSO_REDE_LOCAL.txt") -Encoding ascii -Value @(
    "Movi_commanda - acesso em rede local"
    "URL nesta maquina: http://127.0.0.1:$LocalApiPort/orders/ui"
    "URL para celulares/tablets na mesma rede: http://$lanIPv4`:$LocalApiPort/orders/ui"
    "Porta: $LocalApiPort"
    "Token de pareamento: $((Get-Content -Path $localApiTokenFile -Raw).Trim())"
    "Observacao: conecte os celulares/tablets no mesmo Wi-Fi da maquina servidor."
)

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
wscript //nologo "%~dp0Iniciar_Relatorios_Sync.vbs"
'@ | Set-Content -Path "Iniciar_Relatorios_Sync.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
wscript //nologo "%~dp0Abrir_Status_Relatorios.vbs"
'@ | Set-Content -Path "Abrir_Status_Relatorios.cmd" -Encoding ascii

$statusVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.tray_app", 0, False
"@
$statusVbsContent | Set-Content -Path "Abrir_Status_Relatorios.vbs" -Encoding ascii

$localApiVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m uvicorn agent_local.local_api:app --host 0.0.0.0 --port $LocalApiPort", 0, False
"@
$localApiVbsContent | Set-Content -Path "Abrir_API_Local.vbs" -Encoding ascii

$agentVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.main", 0, False
"@
$agentVbsContent | Set-Content -Path "Iniciar_Relatorios_Sync.vbs" -Encoding ascii

$windowsStartupVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.windows_autostart", 0, False
"@
$windowsStartupVbsContent | Set-Content -Path "Iniciar_Movi_commanda_Windows.vbs" -Encoding ascii

$apiTrayVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.api_tray", 0, False
"@
$apiTrayVbsContent | Set-Content -Path "Abrir_Icone_API.vbs" -Encoding ascii

@'
@echo off
cd /d %~dp0
".\.venv\Scripts\python.exe" -m agent_local.main
pause
'@ | Set-Content -Path "Iniciar_Relatorios_Sync_Debug.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File ".\scripts\set-agent-manual-password.ps1" -Password 25032015
pause
'@ | Set-Content -Path "Definir_Senha_Manual.cmd" -Encoding ascii

@'
@echo off
cd /d %~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\set-local-operator-password.ps1"
pause
'@ | Set-Content -Path "Definir_Senha_Operador_Local.cmd" -Encoding ascii

if (Test-Path ".\scripts\set-agent-manual-password.ps1") {
    Write-Step "Configurando senha local de suporte"
    powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\set-agent-manual-password.ps1" -Password 25032015 | Out-Null
}

Write-Step "Criando atalhos na area de trabalho"
Remove-DesktopShortcutsByPrefix @(
    "Movi"
)
Remove-DesktopShortcutsByTargetRoots $candidateInstallDirs
New-DesktopShortcut -Name "Movi_commanda Definicoes - $packageVersion.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Painel_Local.vbs") -WorkingDirectory $InstallDir
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
Write-Host "4) A API local de comandas inicia junto com o Windows."
Write-Host "5) O sync de relatorios fica separado em Iniciar_Relatorios_Sync.cmd."

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

