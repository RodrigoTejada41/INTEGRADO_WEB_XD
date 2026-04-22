param()
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$doc = Join-Path $projectRoot 'CEREBRO_VIVO.md'
$vaultReadme = Join-Path $projectRoot '.cerebro-vivo\README.md'
if (Test-Path -LiteralPath $doc) {
    Start-Process $doc
}
elseif (Test-Path -LiteralPath $vaultReadme) {
    Start-Process $vaultReadme
}
else {
    Write-Host 'Base local-first nao encontrada.'
}
