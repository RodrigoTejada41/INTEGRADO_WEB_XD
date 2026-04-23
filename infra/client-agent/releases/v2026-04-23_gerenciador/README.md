# Cliente local - Instalador 1 clique

Este pacote instala somente o agente local no Windows, com interface de vinculacao por codigo.

## Execucao rapida

1. Abra `Setup_Gerenciar_Cliente.bat` como administrador.
2. Escolha no menu:
   - verificar status
   - instalar
   - atualizar
   - desinstalar

Atalho direto (instalacao):
- `Setup_Instalar_Cliente.bat`

Depois da instalacao:

2. Apos instalar, execute:
   - `Definir_Senha_Manual.cmd`
   - `Abrir_Vinculacao.cmd`
   - `Iniciar_Agente.cmd`
   - se falhar: `Iniciar_Agente_Debug.cmd`

## Gerar pasta versionada do instalador

No repositorio, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\client-agent\build-release.ps1
```

Isso cria uma pasta em `infra/client-agent/releases/vYYYY-MM-DD_HHMM` com todo o pacote pronto para distribuicao.

## Resultado esperado

- Instalacao em `C:\MoviSyncAgent`
- Virtualenv local com dependencias
- `.env` criado automaticamente
- Tela Python para:
  - vinculacao por codigo
  - troca manual de servidor/chave (protegida por senha)
- Logs de execucao do agente:
  - `C:\MoviSyncAgent\logs\agent-sync.log`
  - `C:\MoviSyncAgent\logs\agent-sync-debug.log`
