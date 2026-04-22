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
