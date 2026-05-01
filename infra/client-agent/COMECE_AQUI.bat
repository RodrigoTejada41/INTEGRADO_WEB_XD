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
echo O instalador vai preparar o agente local em C:\MoviSyncAgent.
echo No final, o painel local sera aberto automaticamente.
echo.
echo No painel, preencha:
echo  1. Codigo de vinculacao fornecido pelo suporte
echo  2. Dados do banco MariaDB local
echo  3. Botao para testar e salvar
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File ".\install-agent-client.ps1" -OpenPanel
if errorlevel 1 (
  echo.
  echo A instalacao falhou.
  echo Envie esta tela para o suporte tecnico.
  pause
  exit /b 1
)

echo.
echo Instalacao concluida.
echo Se o painel nao abriu, use o atalho "MoviSync Painel Local" na area de trabalho.
echo.
pause
exit /b 0
