param(
    [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"
$ordersUrl = "$BaseUrl/orders/ui"

try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 5
    if ($health.status -ne "ok") {
        throw "API local respondeu sem status ok."
    }
} catch {
    throw "API local nao esta acessivel em $BaseUrl. Inicie o MoviSync local antes de abrir pedidos."
}

Start-Process $ordersUrl
