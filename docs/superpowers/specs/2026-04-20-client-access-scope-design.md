# Design: Escopo de Acesso do Cliente e Painel Central

[Agente lider: Software Architect]
[Especialistas de apoio: Backend Engineer, DBA, Security Specialist, Project Manager]

## Contexto

O `sync-admin` hoje mistura duas responsabilidades que precisam ser separadas com mais rigor:

- console operacional da plataforma, usado pela operacao interna;
- portal do cliente, usado apenas para consumo de relatorios.

Ao mesmo tempo, o produto precisa suportar:

- identificacao operacional de APIs conectadas por CNPJ e nome da empresa;
- abertura de relatorios por empresa a partir do painel central;
- acessos de clientes com escopo por empresa inteira ou por conjunto de filiais;
- matriz sempre identificada por `branch_code = 0001`;
- filiais sempre identificadas por `0002`, `0003` e assim por diante.

As regras criticas do repositorio continuam soberanas:

- nunca misturar dados entre empresas;
- sempre usar `empresa_id` em todas as consultas;
- nunca confiar em escopo vindo apenas da interface;
- manter autorizacao e validacao no backend.

## Objetivo

Separar definitivamente o console admin do portal cliente, introduzindo um modelo formal de escopo por empresa ou filial, sem quebrar a governanca multi-tenant.

## Decisoes aprovadas

### 1. Painel admin

O painel admin continua sendo o console central da plataforma.

Responsabilidades:

- cadastrar e gerenciar servidores/APIs que enviam dados;
- acompanhar APIs conectadas;
- identificar clientes por CNPJ e nome da empresa;
- abrir relatorios de qualquer empresa;
- criar e gerenciar acessos de clientes.

Dados minimos esperados na lista de APIs conectadas:

- `empresa_id` / CNPJ formatado;
- nome da empresa;
- status;
- hostname;
- ultimo sync;
- acao para abrir relatorios;
- acao para gerenciar acessos do cliente.

O painel admin nao deve depender de rotas ou navegacao do portal cliente para operar esse fluxo.

### 2. Portal cliente

O portal cliente deve ficar estritamente orientado a relatorios.

Pode ver:

- dashboard;
- relatorios;
- exportacoes;
- filtro por filial dentro do escopo permitido.

Nao pode ver:

- APIs conectadas;
- configuracoes tecnicas;
- logs;
- controle remoto;
- selecao arbitraria de empresa.

### 3. Modelo de acesso

Papeis:

- `admin`: acesso global operacional;
- `client`: acesso restrito a propria empresa.

Escopo do cliente:

- `scope_type = company`
- `scope_type = branch_set`

Comportamento:

- `company`: o cliente acessa toda a propria empresa e, no filtro, pode selecionar qualquer filial da empresa. O estado inicial da tela entra em "todas".
- `branch_set`: o cliente acessa apenas as filiais explicitamente autorizadas. O estado inicial da tela entra em "todas as permitidas".

### 4. Regra de filial

Convencao operacional aprovada:

- matriz = `0001`
- filiais = `0002`, `0003`, ...

A matriz entra no mesmo mecanismo de permissao e filtro das demais filiais.

## Modelagem de dados

### Tabela `users`

Campos relevantes:

- `id`
- `username`
- `full_name`
- `password_hash`
- `role`
- `empresa_id`
- `scope_type`
- `is_active`
- timestamps ja existentes

Regras:

- para `client`, `empresa_id` e `scope_type` sao obrigatorios;
- para `admin`, `scope_type` pode ser nulo;
- `role` continua representando funcao, nao escopo fino.

### Tabela `user_branch_permissions`

Finalidade:

- persistir quais filiais um cliente pode consultar quando seu `scope_type` for `branch_set`.

Campos recomendados:

- `id`
- `user_id`
- `empresa_id`
- `branch_code`
- `can_view_reports`
- `created_at`

Restricoes e indices:

- indice por `user_id`;
- indice por `empresa_id`;
- indice composto por `user_id`, `empresa_id`, `branch_code`;
- unicidade em `user_id + empresa_id + branch_code`.

Regras:

- `scope_type = company`: a tabela pode permanecer vazia;
- `scope_type = branch_set`: a tabela define o conjunto exato de filiais permitidas.

## Regras de autorizacao

### Cliente

O backend deve sempre resolver o escopo real a partir da sessao autenticada.

Regras obrigatorias:

- nunca aceitar `empresa_id` vindo da query string para cliente;
- `empresa_id` sempre vem do usuario autenticado;
- `branch_code` so pode ser aceito se pertencer ao escopo efetivamente autorizado;
- se `scope_type = company`, listar todas as filiais da empresa;
- se `scope_type = branch_set`, listar apenas as filiais da tabela de permissao.

### Admin

Regras obrigatorias:

- pode selecionar qualquer empresa nas rotas administrativas;
- essa selecao nao deve reutilizar implicitamente o comportamento do portal cliente;
- o admin pode abrir relatorios de qualquer empresa a partir do painel central.

## Comportamento das telas

### Tela admin: APIs conectadas

Deve operar como ponto central de entrada.

Fluxo esperado:

1. localizar cliente por CNPJ/nome;
2. abrir relatorios da empresa;
3. gerenciar acessos do cliente.

### Tela admin: gestao de acesso do cliente

Deve permitir:

- criar usuario cliente;
- definir empresa;
- definir `scope_type`;
- se `scope_type = branch_set`, marcar filiais autorizadas (`0001`, `0002`, `0003`, ...).

### Tela cliente: relatorios

Deve:

- ocultar completamente qualquer seletor de empresa;
- exibir apenas filiais permitidas;
- entrar por padrao com "todas" as filiais visiveis dentro do escopo permitido.

## Estrategia de implementacao

Ordem aprovada para reduzir regressao:

1. migracao de banco e modelos:
   - adicionar `scope_type` em `users`;
   - criar `user_branch_permissions`;
2. ajustar schemas e services de usuario;
3. criar uma camada central de resolucao de escopo do cliente;
4. ajustar tela admin para cadastro e edicao de escopo por filial;
5. ajustar portal cliente para respeitar apenas escopo autorizado;
6. ampliar testes de autorizacao e isolamento.

## Testes necessarios

Cobertura minima:

- cliente `company` ve todas as filiais da propria empresa;
- cliente `branch_set` ve apenas filiais marcadas;
- cliente nunca consulta outra empresa;
- cliente nunca seleciona filial fora do proprio escopo;
- admin continua abrindo relatorios de qualquer empresa;
- matriz `0001` aparece como filial valida e respeita permissao.

## Trade-offs

### Pontos fortes

- separa com clareza o console operacional do portal cliente;
- reduz risco de mistura entre tenants;
- modela permissao de forma auditavel e extensivel;
- preserva flexibilidade para empresa inteira ou varias filiais.

### Custos

- exige migracao de schema;
- adiciona complexidade controlada ao cadastro de usuarios cliente;
- exige refatoracao da logica atual de escopo, hoje simplificada em `role + empresa_id`.

## Itens fora de escopo desta entrega

- permissao por terminal;
- permissao por tipo de relatorio;
- multiempresa para o mesmo usuario cliente;
- refatoracoes nao relacionadas do painel admin.

## Validacao do design

Este design foi aprovado em conversa pelo usuario antes da implementacao.
