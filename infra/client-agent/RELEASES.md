# Releases - Cliente Agent

## v2026-04-23_gerenciador

- Adicionado gerenciador completo do instalador:
  - verificar status
  - instalar
  - atualizar (reinstalar pacote atual)
  - desinstalar
- Novos arquivos:
  - `manage-agent-client.ps1`
  - `Setup_Gerenciar_Cliente.bat`
- `install-agent-client.ps1` passou a gravar `release-manifest.txt` na instalacao.

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

