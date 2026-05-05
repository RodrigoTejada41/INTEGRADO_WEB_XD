@echo off
setlocal
title MoviSys - Instalador
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
echo              MoviSys - Instalador
echo ============================================================
echo.
if exist ".\package-version.txt" (
  set /p PACKAGE_VERSION=<".\package-version.txt"
) else (
  set PACKAGE_VERSION=dev-local
)
echo Versao do pacote: %PACKAGE_VERSION%
echo.
echo Este pacote instala a API correta em pasta separada:
echo  - Comanda: C:\Movi_commanda
echo  - Sync Relatorios: C:\MoviSyncAgent
echo.
echo Para configurar vinculo/API ou banco MariaDB, use depois:
echo  - Movi_commanda Definicoes
echo  - MoviSync Relatorios Configurar
echo.
echo Para comandas, use:
echo  - Movi_commanda
echo.
echo Para relatorios, use:
echo  - MoviSync Relatorios Iniciar
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File ".\install-agent-client.ps1" -OpenOrders -PackageKind auto
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
echo Use os atalhos criados na area de trabalho.
echo.
pause
exit /b 0
