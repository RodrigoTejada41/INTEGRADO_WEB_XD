# Releases - Cliente Agent

## v2026-04-22_2258

- Primeiro pacote versionado do instalador cliente.
- Conteudo:
  - instalador 1 clique (`Setup_Instalar_Cliente.bat`)
  - script de instalacao (`install-agent-client.ps1`)
  - runtime necessario (`agent_local/`, `backend/`, `requirements.txt`)
  - scripts de operacao local (`scripts/`)

## Como gerar nova release

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\client-agent\build-release.ps1
```

## Proxima release

- Painel local renomeado para `MoviSync - Painel Local`.
- Nova aba `Banco Local` para configurar MariaDB por formulario.
- Teste real de conexao MariaDB antes de iniciar sincronizacao.
- Atalho novo `Abrir_Painel_Local.cmd`, mantendo compatibilidade com `Abrir_Vinculacao.cmd`.

