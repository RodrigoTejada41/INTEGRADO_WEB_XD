# Historico de Decisoes

## Objetivo deste arquivo

Este historico consolida decisoes relevantes para retomada rapida em modo multi-agentes.
Ele nao substitui a memoria detalhada da `.cerebro-vivo/`; funciona como trilha executiva conectada as fontes canonicas do projeto.

## Fontes canonicas relacionadas

- `.cerebro-vivo/Logs/memory_standard.json`
- `.cerebro-vivo/Logs/processo_projeto.json`
- `.cerebro-vivo/00_PAINEL/PROCESSO_PROJETO.md`

## Decisoes consolidadas

### D001 - Operacao local-first com memoria persistente
- Decisao: consultar primeiro a base local `.cerebro-vivo/` antes de recorrer a fontes externas.
- Motivo: preservar contexto tecnico, continuidade de sessao e rastreabilidade das decisoes.
- Impacto: retomadas ficam mais seguras e reduzem perda de contexto entre tarefas.

### D002 - Governanca oficial em modo multi-agentes
- Decisao: o repositorio passa a operar oficialmente com agente lider, especialistas de apoio e revisao final cruzada.
- Motivo: tarefas deste projeto frequentemente combinam seguranca, dados/logs, produto, backend e arquitetura.
- Impacto: analises ficam mais completas sem enfraquecer as regras criticas multi-tenant.
- Fonte primaria: `AGENTS.md`.

### D003 - Regras criticas continuam soberanas
- Decisao: o modo multi-agentes nao pode relativizar isolamento por `empresa_id`, autenticacao, UUID de sincronizacao, modularidade nem retencao maxima de 14 meses.
- Motivo: essas regras protegem integridade de tenant, compliance tecnico e operacao segura.
- Impacto: qualquer implementacao ou recomendacao deve ser barrada se violar esse conjunto.

### D004 - Memoria executiva top-level sem competir com a base historica
- Decisao: criar `cerebro_vivo/` na raiz com arquivos executivos e manter `.cerebro-vivo/` como base operacional detalhada.
- Motivo: facilitar leitura humana, onboarding e coordenacao multi-agentes sem quebrar a rotina local-first existente.
- Impacto: a raiz ganha uma camada visivel de contexto, enquanto a trilha detalhada continua no repositorio historico.

### D005 - Estado consolidado ate o checkpoint P17
- Decisao: considerar como base atual consolidada os marcos P15, P16 e P17 ja registrados na memoria existente.
- Motivo: eles representam o ponto de continuidade mais recente encontrado na base local.
- Impacto: proximas execucoes podem partir de observabilidade avancada, governanca de segredos e refinamentos finais.

### D006 - Estrutura canonica operacional versus camadas de compatibilidade
- Decisao: tratar `backend/`, `agent_local/`, `sync-admin/` e `infra/` como fontes canonicas operacionais do repositorio.
- Motivo: essa divisao separa a operacao principal do produto das trilhas auxiliares de transicao, onboarding e compatibilidade.
- Impacto: `backend/src`, `frontend`, `database`, `devops` e `docker-compose.yml` na raiz continuam uteis, mas nao redefinem governanca, arquitetura principal nem precedencia operacional.
- Fonte primaria: `AGENTS.md` e `README.md`.

### D007 - P19 fechado com segredos mascarados na superficie administrativa
- Decisao: manter `settings_json` criptografado em repouso e passar a mascarar chaves sensiveis nas respostas admin de configuracao por tenant, sem alterar o uso interno dessas credenciais.
- Motivo: a entrega parcial de P19 ja protegia o armazenamento, mas ainda expunha segredos decriptados nos endpoints administrativos.
- Impacto: a governanca de segredos fica consistente entre persistencia e leitura operacional, preservando isolamento por `empresa_id` e arquitetura em camadas.

### D008 - Auditoria administrativa deve registrar sucesso e falha
- Decisao: rotas administrativas mutantes do backend passam a registrar tambem tentativas com falha, incluindo metadados de requisicao e detalhe resumido do erro.
- Motivo: a auditoria expandida de P19 nao ficava completa enquanto apenas operacoes bem-sucedidas eram persistidas.
- Impacto: investigacao operacional e seguranca ganham trilha mais fiel sem misturar tenants nem expor segredos nos detalhes.

### D009 - P20 fecha a trilha de endurecimento operacional com validacao conservadora
- Decisao: tornar o deploy automatico tolerante a scripts opcionais ausentes, exigir readiness do `sync-admin` no compose de producao e validar a saude dos containers antes do check de borda.
- Motivo: apos P19 e a preparacao de deploy real, a maior aresta encontrada era operacional: o workflow de producao referenciava scripts que nao existiam e a validacao estava rasa para o encadeamento completo.
- Impacto: o deploy fica menos fragil, a cadeia `nginx -> backend -> sync-admin` ganha verificacao mais fiel e o fechamento de P20 permanece de baixo risco, sem alterar isolamento multi-tenant, retencao ou logica de negocio.

### D010 - Backlog pos-P20 passa a ser registrado como tarefas pendentes na memoria executiva
- Decisao: registrar as pendencias pos-P20 explicitamente em `cerebro_vivo/estado_atual.md` e `cerebro_vivo/memoria_projeto.json`, mantendo `historico_decisoes.md` apenas com a regra de priorizacao.
- Motivo: evitar que a continuidade do projeto fique implicita ou espalhada entre respostas de conversa, especialmente apos o fechamento de P20.
- Impacto: a retomada fica mais objetiva, com fila pendente clara e status estruturado, sem confundir backlog futuro com marcos ja concluidos.

### D011 - Pacote `backend.services` deixa de importar configuracao critica em tempo de carga
- Decisao: substituir imports ansiosos no `backend/services/__init__.py` por importacao preguicosa via `__getattr__`.
- Motivo: a coleta de testes e o uso isolado de servicos como `RetentionService` nao devem depender de `Settings()` nem de variaveis obrigatorias que pertencem a outros fluxos do sistema.
- Impacto: o pacote fica mais modular e testavel, reduzindo acoplamento indevido sem alterar regras de negocio, autenticacao ou isolamento multi-tenant.

### D012 - Controle remoto entre `sync-admin` e `receiver-api` adota registro de instalacao + fila de comandos pull
- Decisao: implementar o fluxo bidirecional inicial com `receiver-api` registrando instancias locais, mantendo fila persistente de comandos e snapshots de configuracao/status, enquanto o `sync-admin` processa comandos por polling autenticado com token exclusivo da instalacao.
- Motivo: o acesso remoto a clientes atras de NAT exige um modelo mais seguro que HTTP direto; ao mesmo tempo, o produto precisava de endpoints locais protegidos para configuracao, status e forca de sincronizacao.
- Impacto: a arquitetura ganha uma base SaaS multi-tenant para gerenciamento remoto de instalacoes locais sem abrir excecao para `empresa_id`, autenticacao ou modularidade.

### D013 - Observabilidade do controle remoto passa a ter correlacao ponta a ponta
- Decisao: padronizar `X-Request-Id` e `X-Correlation-Id` no `sync-admin`, propagar a correlacao nas chamadas remotas para o `receiver-api` e expor esse identificador nos logs dos clientes locais.
- Motivo: o fluxo bidirecional ja funcionava, mas ainda faltava um rastro unico e verificavel para diagnostico entre origem local, polling de comandos e recepcao central.
- Impacto: troubleshooting operacional por tenant fica mais rapido sem alterar autenticacao, retencao de 14 meses ou isolamento por `empresa_id`.

### D014 - A web passa a administrar a frota de APIs conectadas via controle central
- Decisao: expor no painel web uma visao central de todas as instancias locais registradas no `receiver-api`, com filtros por `empresa_id`, pagina de detalhe por cliente, leitura de logs e acoes remotas de sincronizacao/configuracao.
- Motivo: a operacao deixou de ser um unico cliente local; o produto precisava administrar via web toda a frota conectada sem depender de acesso direto a cada instalacao.
- Impacto: o `sync-admin` evolui para console operacional centralizado, preservando autenticacao admin, isolamento multi-tenant por `empresa_id` e a arquitetura de polling seguro.

### D015 - Configuracoes de conexao por tenant passam a aceitar referencia segura externa
- Decisao: permitir que `source-configs` e `destination-configs` guardem referencias como `settings_file` ou `settings_env`, com `settings_key` opcional, para resolver host, URL e credenciais apenas no runtime.
- Motivo: a criptografia em repouso ja existia, mas a operacao ainda exigia informar detalhes de conexao diretamente no payload administrativo; isso dificultava onboarding e aumentava exposicao operacional de infraestrutura e segredos.
- Impacto: a API continua multi-tenant por `empresa_id`, mas passa a suportar provisionamento mais seguro e simples, mantendo a superficie administrativa limitada a referencias e nao ao segredo bruto.

### D016 - O cadastro web de servidores de conexao passa a gerar referencia e chave por servidor
- Decisao: adicionar no fluxo administrativo um endpoint dedicado de `secure-configs` e uma tela web para criar conexoes seguras, gravando apenas a referencia no config por tenant e armazenando os segredos em um arquivo central configuravel pelo backend; para conectores de API, a chave de acesso pode ser gerada automaticamente por servidor.
- Motivo: faltava operacionalizar a nova capacidade de referencia segura de modo utilizavel pelo painel, com onboarding simples e sem expor IP, URL ou credenciais na interface administrativa.
- Impacto: o produto passa a ter uma trilha completa para cadastrar servidores via web com isolamento por `empresa_id`, referencia segura reutilizavel e geracao imediata de chave quando o servidor exigir autenticacao por token.

### D017 - A rotacao de credencial por servidor reutiliza a mesma referencia segura
- Decisao: permitir rotacionar a chave do servidor diretamente pela `settings_key`, preservando a configuracao do tenant e atualizando apenas o segredo armazenado no arquivo central.
- Motivo: recriar a configuracao inteira para trocar token era operacionalmente ruim e podia gerar ruído desnecessario em source/destination configs.
- Impacto: a operacao ganha uma trilha segura de renovacao de credencial por servidor, sem expor segredo bruto, sem trocar a referencia usada pelo tenant e sem quebrar o vínculo do painel web com a conexao existente.

### D018 - O segredo do servidor pode ser editado sem trocar a referencia segura
- Decisao: permitir que a web atualize o JSON secreto ligado a uma `settings_key`, com modo `merge` para alterar apenas campos informados e sem recriar a configuracao do tenant.
- Motivo: apos criar o servidor seguro e rotacionar chave, ainda faltava um caminho operacional simples para ajustar URL, headers, regioes ou parametros secretos sem mexer no vínculo da configuracao.
- Impacto: o fluxo seguro fica completo para manutencao operacional do servidor, preservando a mesma referencia (`settings_key`) e mantendo fora do payload administrativo os dados sensiveis reais.

### D019 - O frontend de relatorios passa a nascer sobre a API administrativa multi-tenant
- Decisao: criar uma pagina web dedicada de relatorios no `sync-admin`, consumindo os endpoints administrativos de overview, serie diaria, top produtos e vendas recentes para o `empresa_id` sob controle do painel.
- Motivo: a base de API para relatorios ja existia, mas faltava a primeira camada visual para o operador iniciar leitura analitica sem depender de chamadas manuais ou ferramentas externas.
- Impacto: o produto ganha a primeira entrega concreta do frontend de relatorios, com filtros operacionais e permissao controlada para `admin` e `analyst`, preservando multi-tenant via `empresa_id` e sem bypass de autenticacao.

### D020 - O produto passa a ter trilha separada para cliente com escopo fechado por tenant
- Decisao: introduzir o papel `client` com `empresa_id` obrigatório e rotas dedicadas (`/client/dashboard` e `/client/reports`), impedindo acesso desse perfil às telas administrativas e amarrando a leitura analítica ao tenant do próprio usuário.
- Motivo: o painel precisava deixar de ser apenas uma console interna e passar a suportar uma visão própria para cliente final, sem risco de mistura entre empresas e sem reaproveitar permissões genéricas de admin/analyst.
- Impacto: a separação entre operação central e experiência do cliente fica explícita na autenticação, na navegação e no consumo dos relatórios, reforçando isolamento por `empresa_id` também na camada web.

### D021 - Relatorios web passam a suportar comparativo temporal e exportacao nos dois portais
- Decisao: calcular no `sync-admin` o comparativo entre o periodo filtrado e o periodo anterior equivalente, e expor exportacao de relatorios em `CSV`, `XLSX` e `PDF` tanto para o portal admin quanto para o portal cliente.
- Motivo: a frente de relatorios precisava sair do modo apenas consultivo e passar a oferecer leitura comparativa e compartilhamento/exportacao sem abrir novos riscos de escopo ou exigir endpoints extras no backend.
- Impacto: a camada web ganha analise temporal e distribuicao operacional de relatorios, enquanto o portal cliente continua preso ao `empresa_id` da sessao e nao aceita escopo arbitrario vindo da query string.

### D022 - O stack produtivo local passou a usar porta publica configuravel para evitar conflito com o host
- Decisao: parametrizar a porta publica do Nginx via `NGINX_PUBLIC_PORT` no compose de producao, mantendo `80` como default e usando `8088` apenas no `.env.prod` local desta maquina.
- Motivo: durante a validacao operacional desta sessao, a porta `80` do host estava ocupada e impedia a subida do proxy sem afetar o default de producao.
- Impacto: o ambiente local pode ser validado sem destruir o serviço do host, enquanto a configuracao oficial de producao permanece intacta.

## Linha de continuidade atual

- P15 concluido: migracoes versionadas com rollback por versao/passos
- P16 concluido: health/live/ready no backend e sync-admin
- P17 concluido: backpressure por tenant e retry por classe de falha
- P18 concluido: observabilidade avancada por tenant e correlacao ponta a ponta
- P19 concluido: governanca de segredos e auditoria expandida
- P20 concluido: endurecimento operacional de deploy, readiness e validacao de producao
- Backlog pos-P20 parcialmente avancado: retencao de 14 meses agora possui evidencia automatizada dedicada
- Fluxo bidirecional iniciado: registro de clientes, polling de comandos e controle remoto basico entre `sync-admin` e `receiver-api`
- Observabilidade fim a fim reforcada no controle remoto com `correlation_id` propagado entre `sync-admin` e `backend`
- Painel web centralizado habilitado para listar e administrar todas as APIs conectadas registradas no backend central
- Configuracoes de conexao agora podem ser resolvidas por arquivo/variavel de ambiente com chave nomeada, sem expor credenciais no payload admin
- Cadastro web de servidores seguros agora gera `settings_key` e, quando aplicavel, `api_key` por servidor no momento da criacao
- Chaves de servidores seguros agora podem ser rotacionadas pela web sem recriar a configuracao e sem trocar a `settings_key`
- Campos secretos de servidores seguros agora podem ser editados pela web na mesma `settings_key`, com atualizacao incremental
- Painel `sync-admin` agora possui pagina `/reports` para consumo inicial dos endpoints analiticos multi-tenant do backend
- Painel agora diferencia portal admin e portal cliente, com acesso cliente limitado ao próprio `empresa_id`
- Relatorios dos portais admin e cliente agora suportam comparativo com periodo anterior e exportacao em `CSV`, `XLSX` e `PDF`
- Proximo marco previsto: backlog pos-P20 a priorizar conforme risco operacional e continuidade do produto

## Regra de manutencao

Sempre que houver decisao arquitetural, de seguranca, de dados/logs ou de produto com impacto duradouro, atualizar este arquivo e apontar a fonte detalhada correspondente na `.cerebro-vivo/`.

### D023 - O cliente MoviSync deve recuperar update apos reboot quando houver lock de arquivo no `.venv`
- Decisao: o hotfix de instalacao e desinstalacao do cliente agora encerra processos Python ligados ao diretorio e tenta novamente a remocao antes de falhar.
- Motivo: o bloqueio de `pyd` em uso mostrou que a limpeza do ambiente virtual pode travar em runtime ativo e precisa de tratamento operacional previsivel.
- Impacto: a frente de instalacao do cliente fica menos fragil, mas o procedimento oficial de retomada passa a exigir reboot quando o lock persistir.

### D024 - A reinstalacao do MoviSync deve preservar vinculacao, identidade e checkpoints
- Decisao: o instalador do cliente agora faz backup e restaura `.env`, `agent_api_key.txt`, `local_client_identity.json` e `checkpoints.json` quando `ForceReinstall` e executado.
- Motivo: a reinstalacao nao pode apagar estado funcional do cliente nem forcar nova configuracao quando o objetivo e apenas atualizar o pacote.
- Impacto: o cliente fica recuperavel apos update/reinstall sem perder a identidade de pareamento nem o checkpoint de operacao.

### D025 - O dashboard operacional do sync-admin passa a expor o ciclo real de sincronizacao por fonte
- Decisao: o dashboard principal do `sync-admin` agora mostra `last_scheduled_at`, `next_run_at`, ultimo sucesso e estado de cada `source config`, com fallback rapido quando a API de controle estiver offline.
- Motivo: a operacao precisava sair do modelo de apenas verificar saude/telemetria e passar a enxergar o ciclo de sincronizacao de forma direta e acionavel.
- Impacto: o produto ganha cockpit operacional para acompanhar o que esta pronto para sincronizar agora, sem alterar o motor de sync nem o isolamento por tenant.
- Impacto: a atualizacao do cliente fica menos disruptiva, o launcher pode iniciar oculto sem janela preta e a re-vinculacao passa a depender apenas de um novo pairing code valido quando o anterior expirar.

### D025 - O checkpoint de reboot do cliente MoviSync fica registrado como continuidade principal
- Decisao: consolidar o estado atual de retomada no checkpoint principal, no resumo executivo e no historico antes do reboot, mantendo a suite completa validada e a proxima acao operacional claramente marcada.
- Motivo: a pausa agora depende de reinicio local e o contexto nao pode ficar apenas na conversa.
- Impacto: a continuidade fica pronta para retomada sem redescobrir o estado do cliente, do Nginx e da validacao final.

### D026 - O proxy de borda deve preservar o contrato `/admin/api/` do cliente local
- Decisao: manter `location /admin/api/` separado de `location /admin/` no Nginx de producao, com rewrite proprio para o backend central.
- Motivo: o cliente local registra em `/admin/api/api/v1/register`; se a borda remover apenas `/admin/`, o path efetivo fica incorreto e o cliente nao aparece no painel de APIs conectadas.
- Impacto: a administracao da frota fica consistente com o contrato do agente, sem quebrar o painel administrativo nem os endpoints legados sob `/admin/`.

### D027 - O readiness de producao deve considerar o scheduler real e o schema do tenant_source_configs
- Decisao: o backend de producao passou a considerar o objeto real do scheduler no readiness e o schema da tabela `tenant_source_configs` recebeu `last_scheduled_at` e `next_run_at`.
- Motivo: o boot do backend falhava em VPS por divergencia de schema e a readiness ficava presa em `starting` sem refletir o scheduler em execucao.
- Impacto: o deploy em VPS voltou a ficar saudavel e o endpoint `/admin/api/health/ready` passou a expor o estado correto do sistema.

### D028 - A fonte de verdade executiva foi reconciliada em favor de P20 concluido
- Decisao: considerar `RETOMADA_EXATA.md` e `cerebro_vivo/estado_atual.md` como reconciliados no ponto `P20`, com o deploy VPS validado como estado atual e a divergencia antiga de `P18` encerrada.
- Motivo: havia um checkpoint executivo antigo ainda referindo `P18`, enquanto a producao real, a validacao local e a documentacao operacional ja estavam em `P20`.
- Impacto: retomadas futuras passam a partir de `P20` como linha canonica, com deploy VPS, readiness e rotas `/MoviRelatorios` e `/admin/api/health/ready` como verdade atual.

### D029 - A producao estavel passa a ser o commit `5a06f1d` e o risco atual migra para drift local
- Decisao: registrar `5a06f1d` como linha operacional estavel da VPS e tratar o risco principal atual como drift local de migracoes e testes.
- Motivo: a producao ja foi validada e estabilizada; o que resta agora e alinhar o baseline local ao contrato efetivamente aplicado em VPS.
- Impacto: a continuidade deve priorizar reconciliacao de migrações, rollback e testes de schema no workspace local antes de alterar a producao.
### D030 - A migration `v004` passa a ser a linha base local do contrato de schema
- Decisao: considerar `v004_tenant_source_last_scheduled_at` como baseline atual do contrato de migracao e ajustar os testes de rollback para a sequencia completa 4 -> 3 -> 2 -> 1 -> 0.
- Motivo: o drift local vinha de um teste ainda preso ao estado anterior, enquanto a producao estavel ja opera com a quarta migration aplicada.
- Impacto: o contrato de migracao fica coerente com a linha base atual sem alterar o comportamento de producao nem os segredos do deploy.

### D031 - O intervalo padrao de sincronizacao passa a ser 16 minutos
- Decisao: padronizar o contrato de sincronizacao em 16 minutos como default em `agent_local`, schemas de criacao e defaults ORM do backend.
- Motivo: a arquitetura atual apontava divergencia entre 16 minutos como regra esperada e 15 minutos codificados em partes do fluxo.
- Impacto: a configuracao fica alinhada entre agente local, backend e templates de ambiente, reduzindo drift operacional.

### D032 - O temp root do pytest deve ficar no workspace e nao na home do usuario
- Decisao: fixar o root temporario de teste em `runtime/pytest-tmp` dentro do workspace, configurando `tempfile.tempdir`, `TMPDIR`, `TEMP`, `TMP` e `PYTEST_DEBUG_TEMPROOT`.
- Motivo: a home do usuario tinha ACL quebrada para o path herdado de `.codex/memories/pytest-tmp`, o que causava PermissionError e instabilidade em `tmp_path`.
- Impacto: a suite de testes fica reproducivel neste Windows sem depender da permissao da home, e o comportamento de producao nao e alterado.

### D033 - A sessao do backend deve ser segura por ambiente
- Decisao: usar `ENVIRONMENT=development` como default do backend e habilitar `https_only` no `SessionMiddleware` somente quando `ENVIRONMENT=production`.
- Motivo: o backend estava assumindo producao por default e mantendo cookie de sessao sem restricao de HTTPS em runtime, o que nao e adequado para producao real.
- Impacto: o fluxo local e de teste continua funcional por HTTP, enquanto a producao recebe cookie de sessao mais seguro sem exigir ajustes manuais em cada execucao de desenvolvimento.

### D034 - O ambiente de teste deve ser restaurado apos cada caso
- Decisao: adicionar um fixture autouse em `conftest.py` para restaurar `os.environ` apos cada teste.
- Motivo: a suite estava vazando `ENVIRONMENT=production`, `RATE_LIMIT_*` e segredos entre casos, fazendo testes de desenvolvimento falharem por herdar estado de um teste anterior.
- Impacto: o isolamento da suite fica previsivel, os testes deixam de depender da ordem de execucao e a validacao de producao continua coberta pelos testes dedicados.

### D035 - O runbook de producao passa a ser a referencia operacional unica
- Decisao: consolidar as operacoes recorrentes em `infra/RUNBOOK_PRODUCAO.md` e referenciar esse arquivo no guia de VPS e no README.
- Motivo: o projeto ja tinha scripts e verificacoes, mas faltava um caminho unico e coerente para deploy, update, backup, restore, rollback e health checks.
- Impacto: reduz-se a dispersao de instrucoes, melhora-se a continuidade entre sessoes e a operacao fica mais segura para humanos e outras IAs.

### D036 - O guardrail multi-tenant recebe contrato explicito de validacao
- Decisao: adicionar cobertura de teste para `validate_empresa_id`, `validate_api_key_format` e `generate_api_key`.
- Motivo: o isolamento por tenant nao deve depender apenas de uso correto nas rotas; a validacao base precisa ter contrato verificavel e reutilizavel.
- Impacto: a seguranca de entrada ganha uma camada objetiva de regressao, reduzindo o risco de IDs ou chaves malformadas atravessarem a borda do sistema.

### D037 - O controle remoto local passa a ter allowlist de IP coberta por teste
- Decisao: validar em teste o comportamento de allowlist de IP do `sync-admin` no endpoint de controle local.
- Motivo: o fluxo bidirecional depende de token local e de origem confiavel; sem contrato automatizado, a politica de IP podia regredir silenciosamente.
- Impacto: o pull de comandos e a atualizacao local ficam mais previsiveis em producao, com bloqueio claro quando a origem nao estiver autorizada.

### D038 - A composicao de producao passa a expor apenas o Nginx publicamente
- Decisao: criar contrato de teste para garantir que `backend`, `frontend` e `db` nao tenham porta publica e que apenas o `nginx` publique porta no host.
- Motivo: a VPS deve manter a superficie exposta minimizada, com toda a entrada passando pela borda reversa.
- Impacto: reduz risco de exposicao acidental de servicos internos e torna o contrato de producao verificavel por regressao automatizada.

### D039 - O ciclo remoto do `remote_agent` respeita o pull habilitado e expõe snapshot de comandos
- Decisao: registrar em teste que `run_remote_cycle()` deve retornar imediatamente quando `remote_command_pull_enabled` estiver desabilitado e que o snapshot de status precisa expor `last_command_poll_at`, `last_registration_at`, `pending_local_batches` e `total_local_records`.
- Motivo: o controle remoto do `sync-admin` nao pode executar polling ou registro quando a configuracao local esta desligada, e o painel precisa de um snapshot minimo para diagnostico.
- Impacto: o contrato do fluxo remoto fica protegido contra ativacao indevida e o status operacional ganha campos verificaveis para suporte e auditoria.

### D040 - A fumaça de readiness passa a cobrir a cadeia produtiva inteira em um unico contrato
- Decisao: consolidar o smoke de readiness em um teste que valida backend, sync-admin e o snapshot operacional do `remote_agent`, mantendo o contrato de ciclo desligado no teste dedicado.
- Motivo: a cadeia produtiva precisa de um ponto unico de verificacao para a operacao principal sem misturar responsabilidade de health com comportamento de polling remoto.
- Impacto: o fechamento operacional fica mais simples de auditar e a regressao da cadeia inteira pode ser detectada por um unico teste de fumaça, sem remover a cobertura especializada existente.

### D041 - O comando remoto `force_sync` passa a ter cobertura funcional de efeito real
- Decisao: validar em teste que o comando remoto `force_sync` atualiza o estado local, registra log operacional e retorna `completed` com sucesso.
- Motivo: o fluxo bidirecional nao estava coberto no efeito pratico mais importante, que e sincronizar por comando remoto e registrar rastreabilidade local.
- Impacto: o `sync-admin` ganha uma prova objetiva de que o caminho remoto nao apenas conecta, mas produz efeito verificavel e auditavel no cliente local.

### D042 - A API central recebe um contrato E2E de release
- Decisao: validar em teste o ciclo completo de `provision_tenant`, `register`, `sync`, `rotate_tenant_key` e bloqueio da chave antiga.
- Motivo: a API central precisava de uma prova unica de autenticacao, isolamento por `empresa_id`, ingestao, revogacao e reautorizacao.
- Impacto: o fluxo comercial principal passa a ter um gate de regressao que separa funcionamento parcial de contrato realmente blindado.

### D043 - O contrato E2E da API central tambem precisa rastrear correlation_id
- Decisao: adicionar assercoes de `correlation_id` em auditoria administrativa de provisionamento, rotacao de chave e sync, alem do log do cliente local no registro.
- Motivo: o contrato precisava provar nao apenas resultado funcional, mas tambem rastreabilidade operacional entre admin, sync e cliente.
- Impacto: o gate de release passa a validar observabilidade fim a fim sem depender de inspecao manual em logs ou auditoria.

### D044 - A revogacao web do sync-admin recebe cobertura operacional explicita
- Decisao: validar a rota `/settings/rotate-tenant-key` com login, redirecionamento, flash e aplicacao da nova chave no arquivo do agente.
- Motivo: a revogacao nao podia ficar blindada apenas na API interna; o operador precisa de prova de que a trilha web executa o fluxo completo.
- Impacto: o painel administrativo passa a ter um contrato verificavel de revogacao efetiva, reduzindo risco de rotacao quebrada em producao.

### D045 - O contrato de migrations passa a medir target_version e estado da tabela de migracoes
- Decisao: validar que `upgrade(engine, target_version=3)` para exatamente em 3, grava 3 registros na tabela de migracoes e aplica a quarta migration somente em uma segunda subida.
- Motivo: o drift de schema precisava de um contrato objetivo do runner, nao apenas rollback por steps.
- Impacto: o baseline local fica mais previsivel e a linha de migrations deixa de depender de interpretacao manual do schema criado pela base ORM.

### D046 - A integracao local/VPS ganha contrato E2E simulado em um unico teste
- Decisao: validar em teste unico o fluxo em que o painel local provisiona o tenant na API central simulada, registra o cliente local, roda a visao de APIs conectadas e rotaciona a chave, confirmando o bloqueio da credencial antiga.
- Motivo: faltava uma prova executavel que simulasse os dois pontos da operacao real sem depender de rede externa ou de uma VPS ativa.
- Impacto: a retomada fica mais segura, a integracao local/VPS passa a ter contrato automatico e a regressao entre painel, cadastro central e cliente local fica detectavel em uma unica suite.

### D047 - A simulacao local/VPS tambem valida o ciclo bidirecional de comandos remotos
- Decisao: expandir o contrato local/VPS para enfileirar `force_sync` pelo painel, puxar o comando na API central, registrar o resultado do cliente local e comprovar o ciclo completo sem rede externa.
- Motivo: a prova anterior cobria cadastro e rotacao de chave, mas ainda deixava o caminho bidirecional sem uma validacao integrada no mesmo teste.
- Impacto: o contrato de integracao passa a cobrir nao apenas onboarding e revogacao, mas tambem a operacao remota efetiva da frota conectada.

### D048 - O deploy passa a ter smoke de release executavel e documentado
- Decisao: criar um smoke de release que roda contra a VPS publicada via `RELEASE_SMOKE_BASE_URL`, validando `healthz`, `readyz/backend`, `readyz/sync-admin`, `admin/api/health/ready`, `admin/` e `MoviRelatorios/`.
- Motivo: a simulacao local cobria o contrato funcional, mas faltava um gate especifico para a publicacao real depois do deploy.
- Impacto: o deploy ganha uma prova objetiva de release, a nova feature so avanca se a publicacao continuar saudavel e a operacao manual fica menos subjetiva.
