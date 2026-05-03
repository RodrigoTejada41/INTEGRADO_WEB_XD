@echo off
setlocal
title MoviSync - Instalador do Cliente
cd /d "%~dp0"

net session >nul 2>&1
if not "%errorlevel%"=="0" (
  echo.
  echo Este instalador precisa de permissao de administrador.
  echo Clique em "Sim" na janela do Windows que vai abrir.
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b 0
)

echo ============================================================
echo              MoviSync - Instalador do Cliente
echo ============================================================
echo.
if exist ".\package-version.txt" (
  set /p PACKAGE_VERSION=<".\package-version.txt"
) else (
  set PACKAGE_VERSION=dev-local
)
echo Versao do pacote: %PACKAGE_VERSION%
echo.
echo O instalador vai preparar o agente local em C:\MoviSyncAgent.
echo No final, a tela de Comandas Locais sera aberta automaticamente.
echo.
echo Para configurar vinculo/API ou banco MariaDB, use depois:
echo  - MoviSync Painel Local
echo.
echo Para comandas, use:
echo  - MoviSync Comandas Locais
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File ".\install-agent-client.ps1" -OpenOrders
if errorlevel 1 (
  echo.
  echo A instalacao falhou.
  echo Envie esta tela para o suporte tecnico.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida.
echo Versao instalada: %PACKAGE_VERSION%
echo Se a tela de comandas nao abriu, use o atalho "MoviSync Comandas Locais - %PACKAGE_VERSION%" na area de trabalho.
echo.
pause
exit /b 0
