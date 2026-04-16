$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return "python" }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return "py -3" }

  throw "Python nao encontrado. Instale Python 3."
}

$pyCmd = Resolve-PythonCommand
$env:PYTHONPATH = "packages/shared/src"

Write-Host "[pipeline-once] running ingestion..."
Invoke-Expression "$pyCmd apps/ingestion-service/src/main.py --once"

Write-Host "[pipeline-once] draining reverse/transformation/persistence..."
for ($i = 0; $i -lt 10; $i++) {
  $r = Invoke-Expression "$pyCmd apps/reverse-engineering-service/src/main.py --once"
  $t = Invoke-Expression "$pyCmd apps/transformation-service/src/main.py --once"
  $p = Invoke-Expression "$pyCmd apps/persistence-service/src/main.py --once"

  if (($r -join "`n") -match "processed=0" -and ($t -join "`n") -match "processed=0" -and ($p -join "`n") -match "processed=0") {
    break
  }
}

Write-Host "[pipeline-once] done"
