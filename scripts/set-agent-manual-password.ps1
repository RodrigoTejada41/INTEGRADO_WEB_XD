param(
    [string]$Password = "25032015",
    [string]$Target = "MoviSync.ManualConfig.Password",
    [string]$User = "local-agent"
)

$ErrorActionPreference = "Stop"

cmdkey /generic:$Target /user:$User /pass:$Password | Out-Null
Write-Host "Senha registrada no Windows Credential Manager."
Write-Host "Target: $Target"
