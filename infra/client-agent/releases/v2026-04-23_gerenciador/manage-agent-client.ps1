param(
    [ValidateSet("menu", "status", "install", "update", "uninstall")]
    [string]$Action = "menu",
    [string]$InstallDir = "C:\MoviSyncAgent"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Read-ManifestValue([string]$manifestPath, [string]$key) {
    if (!(Test-Path $manifestPath)) { return $null }
    $line = Select-String -Path $manifestPath -Pattern "^$key=" -SimpleMatch:$false | Select-Object -First 1
    if ($null -eq $line) { return $null }
    return ($line.Line -split "=", 2)[1]
}

function Get-PackageVersion {
    $manifest = Join-Path $packageRoot "release-manifest.txt"
    $version = Read-ManifestValue -manifestPath $manifest -key "version"
    if ([string]::IsNullOrWhiteSpace($version)) { return "dev-local" }
    return $version
}

function Get-InstalledVersion {
    $manifest = Join-Path $InstallDir "release-manifest.txt"
    $version = Read-ManifestValue -manifestPath $manifest -key "version"
    if ([string]::IsNullOrWhiteSpace($version)) { return $null }
    return $version
}

function Show-Status {
    $pkgVersion = Get-PackageVersion
    $instVersion = Get-InstalledVersion
    $isInstalled = Test-Path $InstallDir
    $venvOk = Test-Path (Join-Path $InstallDir ".venv\Scripts\python.exe")
    $envOk = Test-Path (Join-Path $InstallDir ".env")
    $keyOk = Test-Path (Join-Path $InstallDir "agent_local\data\agent_api_key.txt")

    Write-Host ""
    Write-Host "=== STATUS CLIENTE MOVISYNC ==="
    Write-Host "Pacote atual:        $pkgVersion"
    Write-Host "Instalado:           $isInstalled"
    Write-Host "Versao instalada:    $instVersion"
    Write-Host "Virtualenv:          $venvOk"
    Write-Host ".env:                $envOk"
    Write-Host "API key local:       $keyOk"
    Write-Host "Diretorio:           $InstallDir"
    Write-Host ""
}

function Run-Install([bool]$forceReinstall) {
    $installer = Join-Path $packageRoot "install-agent-client.ps1"
    if (!(Test-Path $installer)) {
        throw "install-agent-client.ps1 nao encontrado em $packageRoot"
    }
    if ($forceReinstall) {
        powershell -ExecutionPolicy Bypass -File $installer -InstallDir $InstallDir -ForceReinstall
    } else {
        powershell -ExecutionPolicy Bypass -File $installer -InstallDir $InstallDir
    }
}

function Run-Uninstall {
    if (!(Test-Path $InstallDir)) {
        Write-Host "Nada para desinstalar: $InstallDir nao existe."
        return
    }

    $backupDir = Join-Path $packageRoot "backups"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $envFile = Join-Path $InstallDir ".env"
    if (Test-Path $envFile) {
        Copy-Item $envFile (Join-Path $backupDir "env_backup_$stamp.env") -Force
    }

    Remove-Item -Path $InstallDir -Recurse -Force
    Write-Host "Desinstalacao concluida. Backup .env em $backupDir"
}

function Run-Menu {
    while ($true) {
        Show-Status
        Write-Host "1) Verificar status"
        Write-Host "2) Instalar"
        Write-Host "3) Atualizar (reinstalar versao do pacote)"
        Write-Host "4) Desinstalar"
        Write-Host "5) Sair"
        $opt = Read-Host "Escolha uma opcao"
        switch ($opt) {
            "1" { Show-Status; Read-Host "Enter para continuar" | Out-Null }
            "2" { Run-Install $false; Read-Host "Enter para continuar" | Out-Null }
            "3" { Run-Install $true; Read-Host "Enter para continuar" | Out-Null }
            "4" { Run-Uninstall; Read-Host "Enter para continuar" | Out-Null }
            "5" { break }
            default { Write-Host "Opcao invalida."; Start-Sleep -Seconds 1 }
        }
    }
}

switch ($Action) {
    "status" { Show-Status }
    "install" { Run-Install $false }
    "update" { Run-Install $true }
    "uninstall" { Run-Uninstall }
    default { Run-Menu }
}

