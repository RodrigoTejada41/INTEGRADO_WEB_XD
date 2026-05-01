# Releases - Cliente Agent

## v2026-05-01_facil

- Pacote para instalacao por usuario leigo.
- Novo ponto de entrada:
  - `COMECE_AQUI.bat`
- Fluxo:
  - pede permissao de administrador automaticamente;
  - instala em `C:\MoviSyncAgent`;
  - configura senha local de suporte;
  - cria atalhos na area de trabalho;
  - abre o painel local ao final.
- Mantem compatibilidade:
  - `Setup_Instalar_Cliente.bat` chama o fluxo guiado.
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-01_facil.zip`
- Validacao:
  - pacote contem `COMECE_AQUI.bat`;
  - pacote contem heartbeat `/sync/status`;
  - `py -3 -m compileall infra\client-agent\releases\v2026-05-01_facil\agent_local infra\client-agent\releases\v2026-05-01_facil\backend -q` sem erro.

## v2026-05-01_tray

- Icone `MoviSync` na bandeja do Windows, perto do relogio.
- Menu do icone:
  - iniciar sincronizacao;
  - parar sincronizacao;
  - reiniciar sincronizacao;
  - abrir painel local;
  - abrir log.
- Status visual:
  - verde: sincronizador ativo;
  - vermelho: sincronizador parado.
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-01_tray.zip`
- Validacao:
  - pacote contem `agent_local/tray_app.py`;
  - pacote contem `pystray` e `Pillow` no `requirements.txt` da release;
  - `py -3 -m compileall infra\client-agent\releases\v2026-05-01_tray\agent_local infra\client-agent\releases\v2026-05-01_tray\backend -q` sem erro.

## v2026-05-01_heartbeat

- Pacote atualizado apos deploy do heartbeat de status do agente.
- Inclui:
  - `POST /sync/status` no cliente local;
  - envio de `X-Agent-Device-Label`;
  - heartbeat em ciclos com lote e em ciclos sem registros;
  - compatibilidade com `Status da sincronizacao` exibindo `last_sync_at` real.
- Pasta local:
  - `infra/client-agent/releases/v2026-05-01_heartbeat`
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-01_heartbeat.zip`
- Validacao:
  - pacote contem `send_sync_status`;
  - `py -3 -m compileall infra\client-agent\releases\v2026-05-01_heartbeat\agent_local infra\client-agent\releases\v2026-05-01_heartbeat\backend -q` sem erro.

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

