@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\manage-agent-client.ps1" -Action menu -InstallDir C:\MoviSyncAgent
exit /b %errorlevel%
