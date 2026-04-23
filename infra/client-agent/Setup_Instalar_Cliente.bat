@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\manage-agent-client.ps1" -Action install -InstallDir C:\MoviSyncAgent
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

