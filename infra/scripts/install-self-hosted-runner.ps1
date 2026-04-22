param(
    [Parameter(Mandatory = $true)]
    [string]$RunnerUrl,

    [Parameter(Mandatory = $true)]
    [string]$RegistrationToken,

    [string]$RunnerName = $env:COMPUTERNAME,
    [string]$RunnerVersion = "2.325.0",
    [string]$RunnerFolder = "C:\actions-runner-integrado-web-xd",
    [string]$Labels = "integrado-web-xd,deploy-local",
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"

$runnerZip = Join-Path $env:TEMP "actions-runner-win-x64-$RunnerVersion.zip"
$downloadUrl = "https://github.com/actions/runner/releases/download/v$RunnerVersion/actions-runner-win-x64-$RunnerVersion.zip"

Write-Host "[runner] Preparando pasta $RunnerFolder"
New-Item -ItemType Directory -Force -Path $RunnerFolder | Out-Null

Write-Host "[runner] Baixando runner $RunnerVersion"
Invoke-WebRequest -Uri $downloadUrl -OutFile $runnerZip

Write-Host "[runner] Extraindo runner"
Expand-Archive -LiteralPath $runnerZip -DestinationPath $RunnerFolder -Force

Push-Location $RunnerFolder
try {
    if (Test-Path ".runner") {
        Write-Host "[runner] Runner ja configurado neste diretorio."
        if (-not $ReplaceExisting) {
            throw "Use -ReplaceExisting para reconfigurar o runner neste diretorio."
        }

        Write-Host "[runner] Removendo configuracao anterior local"
        if (Test-Path ".\svc.cmd") {
            & .\svc.cmd stop | Out-Null
            & .\svc.cmd uninstall | Out-Null
        }
        Remove-Item -Force ".runner"
    }

    $configArgs = @(
        "--url", $RunnerUrl,
        "--token", $RegistrationToken,
        "--name", $RunnerName,
        "--labels", $Labels,
        "--work", "_work",
        "--unattended",
        "--runasservice"
    )

    if ($ReplaceExisting) {
        $configArgs += "--replace"
    }

    Write-Host "[runner] Configurando runner self-hosted"
    & .\config.cmd @configArgs

    Write-Host "[runner] Instalando e iniciando servico"
    if (Test-Path ".\svc.cmd") {
        & .\svc.cmd install
        & .\svc.cmd start
    }
    else {
        Write-Warning "svc.cmd nao foi gerado. Verifique sincronizacao de horario do Windows e execute novamente com -ReplaceExisting."
        Write-Warning "Enquanto isso, o runner pode permanecer registrado no GitHub, mas offline."
    }

    Write-Host "[runner] Runner configurado com sucesso."
    Write-Host "[runner] Labels aplicadas: self-hosted, windows, x64, $Labels"
}
finally {
    Pop-Location
}
