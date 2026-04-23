@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\install-agent-client.ps1"
if errorlevel 1 (
  echo.
  echo Instalacao falhou.
  pause
  exit /b 1
)
echo.
echo Instalacao finalizada com sucesso.
pause
exit /b 0

