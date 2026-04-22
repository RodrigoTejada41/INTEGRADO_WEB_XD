param(
    [string]$HostName = "172.238.213.72",
    [string]$UserName = "root",
    [string]$KeyPath = "$HOME\.ssh\movisys_vps",
    [string]$RemoteCommand = ""
)

if (-not (Test-Path $KeyPath)) {
    Write-Error "Chave SSH nao encontrada em: $KeyPath"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($RemoteCommand)) {
    ssh -i $KeyPath "$UserName@$HostName"
    exit $LASTEXITCODE
}

ssh -i $KeyPath "$UserName@$HostName" $RemoteCommand
exit $LASTEXITCODE
