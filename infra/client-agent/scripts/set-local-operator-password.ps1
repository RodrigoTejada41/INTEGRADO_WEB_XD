param(
    [string]$InstallDir = "C:\Movi_commanda"
)

$ErrorActionPreference = "Stop"

$dbPath = Join-Path $InstallDir "agent_local\data\local_orders.db"
$pythonPath = Join-Path $InstallDir ".venv\Scripts\python.exe"

if (!(Test-Path $dbPath)) {
    throw "Banco local nao encontrado: $dbPath"
}
if (!(Test-Path $pythonPath)) {
    throw "Python do pacote nao encontrado: $pythonPath"
}

Write-Host "Usuarios locais:"
& $pythonPath -c @"
import sqlite3
con = sqlite3.connect(r'$dbPath')
for code, name in con.execute("SELECT code, name FROM local_order_operators WHERE active = 1 ORDER BY name"):
    print(f"{code} - {name}")
con.close()
"@

$operator = Read-Host "Digite o codigo ou nome do usuario"
$securePassword = Read-Host "Digite a senha que sera usada nas comandas" -AsSecureString
$passwordPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPtr)
    $env:MOVI_OPERATOR_LOOKUP = $operator
    $env:MOVI_OPERATOR_PASSWORD = $plainPassword
    & $pythonPath -c @"
import hashlib
import os
import secrets
import sqlite3

db_path = r'$dbPath'
lookup = os.environ['MOVI_OPERATOR_LOOKUP'].strip()
password = os.environ['MOVI_OPERATOR_PASSWORD']

def pbkdf2(value: str, iterations: int = 210000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', value.encode('utf-8'), salt, iterations)
    return f'pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}'

con = sqlite3.connect(db_path)
row = con.execute(
    "SELECT code, name FROM local_order_operators WHERE active = 1 AND (code = ? OR upper(name) = upper(?))",
    (lookup, lookup),
).fetchone()
if row is None:
    raise SystemExit('Usuario local nao encontrado.')
con.execute("UPDATE local_order_operators SET password_hash = ? WHERE code = ?", (pbkdf2(password), row[0]))
con.commit()
con.close()
print(f"Senha local atualizada para: {row[1]} ({row[0]})")
"@
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPtr)
    Remove-Item Env:\MOVI_OPERATOR_LOOKUP -ErrorAction SilentlyContinue
    Remove-Item Env:\MOVI_OPERATOR_PASSWORD -ErrorAction SilentlyContinue
}
