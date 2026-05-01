param(
    [string]$InstallDir = "C:\MoviSyncAgent",
    [switch]$OpenPanel
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[instalador] $Message"
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
New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "logs") | Out-Null

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

$panelVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run """" & "$InstallDir\.venv\Scripts\pythonw.exe" & """ -m agent_local.pairing_ui", 0, False
"@
$panelVbsContent | Set-Content -Path "Abrir_Painel_Local.vbs" -Encoding ascii

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

$agentVbsContent = @"
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "$InstallDir"
shell.Run "cmd /c ""$InstallDir\.venv\Scripts\python.exe -m agent_local.main >> $InstallDir\logs\agent-sync.log 2>&1""", 0, False
"@
$agentVbsContent | Set-Content -Path "Iniciar_Agente.vbs" -Encoding ascii

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
New-DesktopShortcut -Name "MoviSync Painel Local.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Painel_Local.vbs") -WorkingDirectory $InstallDir
New-DesktopShortcut -Name "MoviSync Status do Sync.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Status_Sync.vbs") -WorkingDirectory $InstallDir
New-DesktopShortcut -Name "MoviSync Iniciar Agente.lnk" -TargetPath (Join-Path $InstallDir "Abrir_Status_Sync.vbs") -WorkingDirectory $InstallDir

Pop-Location

Write-Step "Instalacao concluida."
Write-Host ""
Write-Host "Proximos passos no painel local:"
Write-Host "1) Informe o codigo de vinculacao."
Write-Host "2) Configure o banco MariaDB local."
Write-Host "3) Clique para testar e salvar."
Write-Host "4) Use o icone perto do relogio para iniciar, parar ou reiniciar."

if ($OpenPanel) {
    Write-Step "Abrindo painel local"
    Start-Process -FilePath "wscript.exe" -ArgumentList @("//nologo", (Join-Path $InstallDir "Abrir_Painel_Local.vbs")) -WorkingDirectory $InstallDir -WindowStyle Hidden
    Write-Step "Abrindo icone de status"
    Start-Process -FilePath "wscript.exe" -ArgumentList @("//nologo", (Join-Path $InstallDir "Abrir_Status_Sync.vbs")) -WorkingDirectory $InstallDir -WindowStyle Hidden
}

