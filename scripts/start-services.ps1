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

Start-Process powershell -ArgumentList "-NoExit", "-Command", "$env:PYTHONPATH='packages/shared/src'; $pyCmd apps/ingestion-service/src/main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$env:PYTHONPATH='packages/shared/src'; $pyCmd apps/reverse-engineering-service/src/main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$env:PYTHONPATH='packages/shared/src'; $pyCmd apps/transformation-service/src/main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$env:PYTHONPATH='packages/shared/src'; $pyCmd apps/persistence-service/src/main.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$env:PYTHONPATH='packages/shared/src'; $pyCmd -m uvicorn apps.api-service.src.main:app --host 0.0.0.0 --port 8080"

Write-Host "Servicos iniciados em novas janelas PowerShell."
