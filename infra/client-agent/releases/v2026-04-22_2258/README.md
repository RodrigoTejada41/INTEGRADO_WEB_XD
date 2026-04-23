# Cliente local - Instalador 1 clique

Este pacote instala somente o agente local no Windows, com interface de vinculacao por codigo.

## Execucao rapida

1. Abra `Setup_Instalar_Cliente.bat` como administrador.
2. Apos instalar, execute:
   - `Definir_Senha_Manual.cmd`
   - `Abrir_Vinculacao.cmd`
   - `Iniciar_Agente.cmd`

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
