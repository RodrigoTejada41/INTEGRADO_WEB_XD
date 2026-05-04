# Releases - Cliente Agent

## Procedimento obrigatorio de fechamento

- Ao concluir qualquer ajuste funcional do cliente/comanda, gerar release versionada.
- Usar tag incremental do pacote, exemplo: `v2026-05-04_comandas_r24`.
- Gerar pasta com `infra/client-agent/build-release.ps1`.
- Gerar ZIP em `release-artifacts/Movi_commanda_Installer_<tag>.zip`.
- Validar ZIP sem `__pycache__`, sem `.pyc`, sem `.env` e sem `local_orders.db`.
- Registrar neste arquivo e em `RETOMADA_EXATA.md`:
  - tag;
  - ZIP;
  - tamanho;
  - validacoes executadas.

## v2026-05-04_comandas_r24

- Release para impressao automatica por grupo de produto e permissao de fechar conta.
- Backend local:
  - adiciona cadastro de impressora por grupo em `local_order_group_printers`;
  - adiciona `GET/PUT /orders/technical/printers/groups`;
  - separa itens por familia/grupo ao registrar pedidos via `/orders` e `/orders/confirm`;
  - gera um ticket por grupo e envia para a impressora cadastrada;
  - mantem ticket em job local quando o envio nao for possivel.
- UI/permissao:
  - botao `CONTA` renomeado para `FECHAR CONTA`;
  - fechamento exige permissao `order.close`;
  - usuario sem permissao recebe aviso operacional.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r24.zip`
- Tamanho validado:
  - `180567` bytes
- Validacao:
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `20 passed`;
  - `py -3 -m pytest -q` com `89 passed, 1 skipped`;
  - ZIP validado sem `__pycache__`, sem `.pyc`, sem `.env` e sem `local_orders.db`.

## v2026-05-04_comandas_r23

- Release corretiva para cor visual de mesa ocupada no XD.
- Diagnostico:
  - itens estavam em `tmpdocumentstables`;
  - painel continuava verde porque `xconfigsalezonesareaobjects` nao era atualizado;
  - mesa `100` nao tinha registro visual nessa tabela.
- Backend local:
  - atualiza `Status`, `Total`, `LoginDate`, `LogoutDate`, `Terminal` e `NumberPersons`;
  - cria registro visual da mesa quando ausente;
  - calcula total visual com taxa de servico ativa em `xconfig`;
  - limpa estado visual quando nao houver itens abertos.
- Validacao real:
  - mesa `3` ficou `Status=1`, `Total=1752.300`;
  - mesa `100` ficou `Status=1`, `Total=298.100`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r23.zip`
- Tamanho validado:
  - `179123` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `18 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `87 passed, 1 skipped`.

## v2026-05-04_comandas_r22

- Release corretiva para entrada real das comandas na tela do XD.
- Diagnostico:
  - app local gravava em `local_orders` e `local_order_outbox`;
  - XD mostra comandas abertas a partir de `tmpdocumentstables`;
  - `SaleZoneAreaObjectId` e o numero da mesa/comanda.
- Backend local:
  - novo `XDOpenOrdersWriter`;
  - cria/atualiza linhas em `tmpdocumentstables`;
  - usa `ParentGuid` com UUID local para evitar duplicacao;
  - grava mapeamento em `local_order_xd_sync`;
  - adiciona `POST /orders/sync-xd` para reenviar pendentes.
- Instalador:
  - define `LOCAL_ORDER_PUSH_XD_ENABLED=true`;
  - define `LOCAL_ORDER_XD_TERMINAL_ID=1`.
- Validacao real:
  - mesa `3` sincronizada para pedido XD `190`, total `1239.00`;
  - mesa `100` sincronizada para pedido XD `189`, total `271.00`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r22.zip`
- Tamanho validado:
  - `178424` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `18 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `87 passed, 1 skipped`.

## v2026-05-04_comandas_r21

- Release de alinhamento da nomenclatura XD.
- Regra:
  - `COMANDA` no XD foi substituida por `MESA`;
  - no app local, `Mesa` e `command_number` sao o mesmo identificador operacional;
  - campo antigo `Mesa` virou `Referencia`.
- UI:
  - campo principal agora e `Mesa`;
  - `Referencia` e opcional;
  - listagem, revisao e pre-conta mostram `Mesa` e `Referencia`.
- API:
  - payload legado com `table_reference` sem `command_number` e normalizado para `command_number`.
- Impressao:
  - recibo termico usa `MESA`;
  - campo auxiliar usa `Referencia`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r21.zip`
- Tamanho validado:
  - `174396` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `18 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `87 passed, 1 skipped`.

## v2026-05-04_comandas_r20

- Release corretiva para senha local de operador XD.
- Diagnostico:
  - `users.Password` no MariaDB tem 64 caracteres hexadecimais;
  - nao e senha em texto;
  - SQLite local tinha hash, mas gerado sobre o valor importado errado.
- Backend local:
  - suporta hash importado `xd_sha256$...`;
  - no servidor local, se login falhar, grava PBKDF2 da senha digitada para o operador e autentica.
- Utilitario local:
  - `Definir_Senha_Operador_Local.cmd`;
  - `scripts/set-local-operator-password.ps1`;
  - permite definir a senha local sem expor senha no chat.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r20.zip`
- Tamanho validado:
  - `174366` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `18 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `87 passed, 1 skipped`.

## v2026-05-04_comandas_r19

- Release corretiva para erro de token local invalido na UI.
- UI:
  - adiciona `localFetch`;
  - quando recebe `Local token invalid.` no servidor local, busca token atual em `/orders/local-token`;
  - atualiza o campo `TOKEN LOCAL`;
  - repete a chamada automaticamente uma vez.
- Seguranca:
  - auto token continua restrito a `127.0.0.1`, `localhost` e `::1`;
  - celular/tablet continua usando token de `ACESSO_REDE_LOCAL.txt`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r19.zip`
- Tamanho validado:
  - `172974` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `16 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `85 passed, 1 skipped`.

## v2026-05-04_comandas_r18

- Release corretiva do tray de status web.
- Ajustes:
  - timeout do tray para `/orders/technical/status` aumentado para 15s;
  - monitoramento automatico reduzido para 30s para evitar consulta pesada de rede a cada 5s.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r18.zip`
- Tamanho validado:
  - `172736` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `16 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `85 passed, 1 skipped`.

## v2026-05-04_comandas_r17

- Release com IP do servidor e contador de clientes web no icone da API.
- API local:
  - `GET /orders/technical/status` retorna `web_clients_count`;
  - contagem web exclui localhost/testclient.
- Icone `Movi_commanda API`:
  - mostra status da API;
  - mostra IP/URL do servidor;
  - mostra clientes web conectados;
  - adiciona botao `Ver clientes conectados`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r17.zip`
- Tamanho validado:
  - `172736` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `16 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `85 passed, 1 skipped`.

## v2026-05-04_comandas_r16

- Release com icone da API local na bandeja do Windows.
- Adicionado:
  - `agent_local/api_tray.py`;
  - icone `Movi_commanda API` perto do relogio;
  - status verde quando `/health` responde;
  - status vermelho quando API local nao responde.
- Menu do icone:
  - abrir comandas;
  - abrir configuracoes;
  - iniciar API local;
  - reiniciar API local;
  - abrir log da API.
- Autostart:
  - inicia API local de comandas;
  - inicia icone da API;
  - continua sem iniciar `agent_local.main` e sem iniciar `agent_local.tray_app`.
- Instalador:
  - cria `Abrir_Icone_API.vbs`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r16.zip`
- Tamanho validado:
  - `172171` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `15 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `84 passed, 1 skipped`.

## v2026-05-04_comandas_r15

- Release corretiva para login de usuarios importados do MariaDB.
- Causa corrigida:
  - usuarios eram importados para o combo;
  - senha nao era importada;
  - `local_order_operators.password_hash` ficava vazio;
  - login falhava com `Usuario ou senha invalido.`.
- API/local cache:
  - importa senha quando existir coluna `Password`, `PassWord`, `Senha`, `Pass`, `Pwd` ou `UserPassword`;
  - grava somente hash PBKDF2 no SQLite local;
  - reimportacao sem senha preserva hash existente.
- Instalador:
  - evita encerrar o proprio PowerShell durante parada de processos antigos.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-04_comandas_r15.zip`
- Tamanho validado:
  - `170150` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `15 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `84 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`.

## v2026-05-03_comandas_r13

- Release corretiva para reduzir erro de `Local token invalid` ao configurar banco no proprio servidor.
- API local:
  - adiciona `GET /orders/local-token`;
  - endpoint retorna token somente para acesso loopback (`127.0.0.1`, `localhost`, `::1`).
- UI:
  - ao abrir `USUARIOS` ou `DEFINICOES` pelo proprio servidor, tenta preencher automaticamente o token local;
  - mensagem de erro de token agora orienta onde buscar o token para celulares/tablets.
- Seguranca:
  - token nao e exposto para clientes da rede;
  - celulares/tablets continuam usando token de `C:\Movi_commanda\ACESSO_REDE_LOCAL.txt`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r13.zip`
- Tamanho validado:
  - `169953` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `14 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `83 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`.

## v2026-05-03_comandas_r12

- Release com padrao de banco local ja preenchido.
- Defaults aplicados:
  - host: `127.0.0.1`;
  - porta: `3308`;
  - usuario: `root`;
  - senha: `root`;
  - tipo: `mariadb`.
- Pontos atualizados:
  - `agent_local/config/database_config.py`;
  - painel Tkinter de definicoes;
  - painel web tecnico de banco;
  - schemas da API tecnica;
  - fallback da API local quando `AGENT_MARIADB_URL` nao existir.
- Regra mantida:
  - se existir `AGENT_MARIADB_URL` no `.env`, a API puxa a configuracao existente;
  - senha nao e retornada em resposta;
  - senha nao entra em logs.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r12.zip`
- Tamanho validado:
  - `169530` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py tests\test_agent_local_database_config.py -q` com `15 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `82 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`.

## v2026-05-03_comandas_r11

- Release com separacao operacional entre comandas e sync de relatorios.
- `Movi_commanda AutoStart` agora inicia somente:
  - API local de comandas (`agent_local.local_api`);
  - rotas `/orders/*`;
  - UI `/orders/ui`.
- O autostart nao inicia mais:
  - `agent_local.main`;
  - `agent_local.tray_app`;
  - sync de relatorios.
- Sync de relatorios fica separado em:
  - `Iniciar_Relatorios_Sync.cmd`;
  - `Iniciar_Relatorios_Sync.vbs`;
  - `Abrir_Status_Relatorios.cmd`;
  - `Abrir_Status_Relatorios.vbs`.
- Tray do sync renomeado para:
  - `Movi_relatorios_sync`
- Resultado:
  - comandas e relatorios continuam no mesmo pacote fisico;
  - processos e inicializacao ficam separados;
  - a comanda nao sobe mais o sync de relatorios junto.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r11.zip`
- Tamanho validado:
  - `169418` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `12 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `81 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - release validada sem `agent_local.main` e sem `agent_local.tray_app` no `windows_autostart.py`.

## v2026-05-03_comandas_r10

- Release com recursos de rede, conexao e manutencao tecnica do servidor local.
- UI de definicoes:
  - exibe `IP local automatico`;
  - lista IPs locais detectados para escolha;
  - exibe URL de conexao para celulares/tablets;
  - permite copiar a URL;
  - adiciona area inferior com botoes de manutencao:
    - reiniciar servico;
    - verificar conexao;
    - clientes conectados;
    - IP de conexao;
    - banco de dados.
- Endpoints tecnicos adicionados:
  - `GET /orders/technical/network`;
  - `POST /orders/technical/check`;
  - `GET /orders/technical/clients`;
  - `GET /orders/technical/status`;
  - `POST /orders/technical/restart-service`;
  - `GET /orders/technical/database`;
  - `POST /orders/technical/database/test`;
  - `PUT /orders/technical/database`.
- Banco/configuracao:
  - painel para tipo, host, porta, banco, usuario e senha;
  - senha nao retorna em resposta;
  - logs nao registram senha;
  - salvar banco exige teste de conexao com sucesso.
- Seguranca:
  - endpoints tecnicos sensiveis exigem `X-Local-Token`;
  - exigem sessao de usuario `X-Order-Session`;
  - exigem permissao `technical.admin`.
- Clientes conectados:
  - rastreia IP, user agent, usuario logado quando houver sessao, ultimo acesso e status online/offline.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r10.zip`
- Tamanho validado:
  - `169346` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `12 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `81 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`.

## v2026-05-03_comandas_r9

- Release para operacao em rede local com varios celulares/tablets.
- API local:
  - passa a escutar em `0.0.0.0:8765`;
  - mantem acesso local em `http://127.0.0.1:8765/orders/ui`;
  - permite acesso na rede pelo IP da maquina servidor.
- Instalador:
  - cria `C:\Movi_commanda\ACESSO_REDE_LOCAL.txt` com URL local, URL para celulares/tablets, porta e token local;
  - cria regra de firewall `Movi_commanda API Local` para entrada TCP `8765` em rede privada;
  - melhora deteccao de IP LAN, ignorando adaptadores virtuais comuns.
- Cache local:
  - `local_orders.db` continua como cache/controle central da operacao;
  - SQLite configurado com `WAL`, `busy_timeout=30000` e `synchronous=NORMAL` para suportar multiplos dispositivos na rede local.
- Autostart:
  - usa `LOCAL_API_HOST` e `LOCAL_API_PORT` quando configurados;
  - default de host agora e `0.0.0.0`;
  - adicionada trava `windows-autostart.lock` para reduzir inicializacoes duplicadas.
- Validacao nesta maquina:
  - `http://192.168.15.4:8765/health` -> HTTP 200;
  - arquivo atual `C:\Movi_commanda\ACESSO_REDE_LOCAL.txt` aponta para `http://192.168.15.4:8765/orders/ui`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r9.zip`
- Tamanho validado:
  - `164449` bytes
- Validacao:
  - parser PowerShell do instalador sem erro;
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `11 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `80 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`.

## v2026-05-03_comandas_r8

- Release corretiva para falha de tela preta ao abrir comandas.
- Causa raiz:
  - instalador continuava mesmo quando `pip install` falhava;
  - `psycopg2-binary==2.9.9` falhava no Python 3.13 por ausencia de wheel e tentava compilar sem `pg_config`;
  - a venv ficava sem `uvicorn`, `pydantic` e `pystray`, entao a API local nao subia.
- Correcoes:
  - `psycopg2-binary` atualizado para `2.9.10`;
  - instalador agora usa `Invoke-CheckedCommand` para interromper em erro de comando externo;
  - instalador prefere Python `3.12`, depois `3.11`, e so entao `3`;
  - instalador valida importacao de `fastapi`, `uvicorn`, `pydantic`, `pystray` e `PIL` apos instalar dependencias.
- Reparo aplicado nesta maquina:
  - `C:\Movi_commanda\requirements.txt` ajustado para `psycopg2-binary==2.9.10`;
  - dependencias reinstaladas na venv;
  - API local validada em `http://127.0.0.1:8765/health`;
  - `/orders/ui` validado com HTTP 200.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r8.zip`
- Tamanho validado:
  - `163103` bytes
- Validacao:
  - parser PowerShell do instalador sem erro;
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `10 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `79 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`.

## v2026-05-03_comandas_r7

- Release corretiva para reduzir poluicao na area de trabalho.
- Instalador agora:
  - remove atalhos antigos por prefixo `Movi`;
  - remove atalhos cujo destino ou pasta de trabalho apontem para `C:\MoviSyncAgent` ou `C:\Movi_commanda`;
  - cria somente dois atalhos na area de trabalho:
    - `Movi_commanda`;
    - `Movi_commanda Definicoes`;
  - nao cria atalhos de API local, status ou iniciar servico na area de trabalho.
- Limpeza local executada nesta maquina:
  - atalhos antigos movidos para `C:\Users\Rodrigo Tejada\Desktop\Movi_commanda_residuos_20260503_213155`;
  - `config.json` mantido porque pertence a Steam, nao ao Movi_commanda.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r7.zip`
- Tamanho validado:
  - `162799` bytes
- Validacao:
  - parser PowerShell do instalador sem erro;
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `10 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `79 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - release contem somente os atalhos `Movi_commanda` e `Movi_commanda Definicoes` no instalador.

## v2026-05-03_comandas_r6

- Release corretiva para instalacao limpa da marca `Movi_commanda`.
- Instalador agora:
  - instala por padrao em `C:\Movi_commanda`;
  - para processos antigos do aplicativo antes da troca;
  - preserva `.env`, tokens locais, checkpoints e `local_orders.db`;
  - remove instalacoes antigas em `C:\MoviSyncAgent` e na pasta nova antes de copiar arquivos;
  - remove atalhos antigos da area de trabalho e inicializacao do Windows;
  - recria atalhos apenas como `Movi_commanda`;
  - gera script de inicializacao `Iniciar_Movi_commanda_Windows.vbs`.
- Painel Tkinter:
  - titulo `Movi_commanda - Definicoes`;
  - banco padrao visual vazio, sem exibir `xd` por default.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r6.zip`
- Tamanho validado:
  - `162686` bytes
- Validacao:
  - parser PowerShell do instalador sem erro;
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `10 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `79 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - release contem `package-version.txt` com `v2026-05-03_comandas_r6`.

## v2026-05-03_comandas_r5

- Release com menu inicial e identidade `Movi_commanda`.
- Remove referencias visuais antigas da UI/API local de comandas:
  - `XD`;
  - `XD Orders`;
  - `XDOrders`;
  - `Comandas Locais`;
  - `MoviSync`.
- Inclui:
  - menu inicial com marca, versao e botoes `USUARIOS`, `DEFINICOES`, `INICIAR`;
  - tela `DEFINICOES` com servidor, impressora Bluetooth, outras configuracoes, ajuda e sobre;
  - persistencia local em `local_commanda_settings`;
  - endpoints de app-info, settings, teste de conexao, carga de dados, licenca e validacao de licenca.
- Referencias externas de banco reaproveitadas:
  - `items`;
  - `itemsgroups`;
  - `operators`;
  - `xconfigoperators`;
  - `Documentsbodys`;
  - `Documentsheaders`;
  - `salesdocumentsreportview`.
- ZIP de entrega:
  - `release-artifacts/Movi_commanda_Installer_v2026-05-03_comandas_r5.zip`
- Tamanho validado:
  - `161759` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `9 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `78 passed, 1 skipped`;
  - busca em `agent_local/orders/ui.py` e `agent_local/local_api.py` sem nomes antigos.

## v2026-05-03_comandas_r4

- Release com tela principal operacional no estilo do print.
- Mantem separacao:
  - API de comandas locais: `/orders/*`;
  - API de sync de relatorios: sem mistura.
- Inclui:
  - cabecalho com avatar/perfil do operador;
  - botoes `CAIXA DE SAIDA` e `MENSAGENS`;
  - botao central `CONTROLE POR VOZ`;
  - grade 3x3 com `PEDIR`, `ANULAR`, `SUBTOTAL`, `CONTA`, `TRANSFERENCIA`, `PAGAMENTO PARCIAL`, `OUTROS`, `DESCONTO`, `MENU INICIAL`;
  - endpoints de permissoes, subtotal, conta, anulacao, transferencia, pagamento parcial, desconto, mensagens, outbox e voz planejada;
  - tabelas locais de permissoes, logs de operacao, mensagens, pagamentos parciais, descontos, anulacoes e transferencias.
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas_r4.zip`
- Tamanho validado:
  - `164114` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `8 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `77 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - ZIP contem `agent_local\orders\ui.py`;
  - `package-version.txt` contem `v2026-05-03_comandas_r4`.

## v2026-05-03_comandas_r3

- Release com fluxo mobile completo de comandas locais.
- Separacao explicita:
  - API de comandas locais: `/orders/*`;
  - API de sync de relatorios: mantida separada.
- Inclui:
  - login por usuario do banco local;
  - senha com hash PBKDF2 em `local_order_operators.password_hash`;
  - sessao local por `X-Order-Session`;
  - carrinho temporario antes de confirmar pedido;
  - revisao com quantidade, exclusao, observacao, lixeira geral e totais;
  - busca de produto por nome ou codigo;
  - layout responsivo para celular/tablet.
- Atalho principal esperado:
  - `MoviSync Comandas Locais - v2026-05-03_comandas_r3.lnk`
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas_r3.zip`
- Tamanho validado:
  - `158464` bytes
- Validacao:
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `7 passed`;
  - `py -3 -m compileall agent_local -q` sem erro;
  - `py -3 -m pytest -q` com `76 passed, 1 skipped`;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - ZIP contem `agent_local\orders\ui.py`;
  - `package-version.txt` contem `v2026-05-03_comandas_r3`.

## v2026-05-03_comandas_r2

- Release correta para teste das comandas locais.
- Evita confusao com pacotes anteriores:
  - inclui `package-version.txt`;
  - grava `C:\MoviSyncAgent\VERSAO_INSTALADA.txt`;
  - copia `release-manifest.txt` para `C:\MoviSyncAgent`;
  - remove atalhos antigos `MoviSync *.lnk` da area de trabalho antes de criar novos;
  - cria atalhos com versao no nome.
- Atalho principal:
  - `MoviSync Comandas Locais - v2026-05-03_comandas_r2.lnk`
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas_r2.zip`
- Tamanho validado:
  - `151236` bytes
- Validacao:
  - `package-version.txt` contem `v2026-05-03_comandas_r2`;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - ZIP contem `agent_local\orders\*.py`;
  - parser PowerShell OK;
  - `py -3 -m pytest tests\test_agent_local_orders.py -q` com `7 passed`.

## v2026-05-03_comandas

- Pacote oficial com comandas locais separadas da API de sync de relatorios.
- Inclui API operacional local:
  - `/orders`
  - `/orders/ui`
  - `/orders/{uuid}/prebill`
  - `/orders/{uuid}/thermal-receipt`
  - `/orders/{uuid}/print`
- Inclui persistencia SQLite local para comandas, itens, pagamentos, operadores, produtos e outbox.
- Inclui descoberta de catalogo do XD para produtos, familias e operadores.
- Instalador cria atalho:
  - `MoviSync Comandas Locais.lnk`
- ZIP de entrega:
  - `release-artifacts/MoviSyncAgent_Installer_v2026-05-03_comandas.zip`
- Tamanho validado:
  - `150580` bytes
- Validacao:
  - `py -3 -m pytest -q` com `76 passed, 1 skipped`;
  - `py -3 -m compileall infra\client-agent\releases\v2026-05-03_comandas\agent_local infra\client-agent\releases\v2026-05-03_comandas\backend -q` sem erro;
  - ZIP sem `__pycache__` e sem `.pyc`;
  - ZIP contem `agent_local\orders\*.py`.

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
- Hotfix aplicado:
  - atalhos do Painel Local e Status abrem via `.vbs` com `pythonw.exe`;
  - evita tela preta ao iniciar o sincronizador;
  - corrige abertura do botao Painel Local no instalador.
- Hotfix adicional:
  - menu do icone abre Painel Local via `.vbs`;
  - iniciar sincronizacao pelo icone usa `pythonw.exe`.
- Hotfix autostart:
  - cria `MoviSync AutoStart.lnk` na inicializacao do Windows;
  - sobe API local em `http://127.0.0.1:8765`;
  - sobe tray e sync junto com o login do Windows;
  - evita processos duplicados por verificacao de command line.
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

Depois compacte a pasta gerada para `release-artifacts/Movi_commanda_Installer_<tag>.zip`, valide o conteudo e registre o resultado nesta lista.

## Proxima release

- Painel local renomeado para `MoviSync - Painel Local`.
- Nova aba `Banco Local` para configurar MariaDB por formulario.
- Teste real de conexao MariaDB antes de iniciar sincronizacao.
- Atalho novo `Abrir_Painel_Local.cmd`, mantendo compatibilidade com `Abrir_Vinculacao.cmd`.

