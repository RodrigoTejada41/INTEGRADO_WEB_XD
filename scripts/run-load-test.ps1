$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return "python" }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return "py -3" }

  throw "Python nao encontrado. Instale Python 3."
}

$pyCmd = Resolve-PythonCommand

& $pyCmd scripts/db_migrate.py
& $pyCmd scripts/load_test.py --base-url http://127.0.0.1:8000 --requests 25 --concurrency 5
