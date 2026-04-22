# AGENTS.md

## VISAO GERAL DO PROJETO

Este projeto e uma plataforma de sincronizacao de dados multi-tenant.

Arquitetura:
- Agentes locais (MariaDB)
- API central (FastAPI)
- Banco central (PostgreSQL)

Objetivos principais:
- Sincronizar dados a cada 15 minutos
- Garantir isolamento rigoroso por empresa
- Manter apenas 14 meses de dados no banco principal

## ORDEM DE PRECEDENCIA

Em caso de duvida, seguir esta ordem:
1. Regras criticas deste `AGENTS.md`
2. Regras de arquitetura, seguranca, banco e retencao deste `AGENTS.md`
3. Modo oficial multi-agentes definido neste `AGENTS.md`
4. [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md) como modelo operacional de resposta e execucao senior
5. README e base local de continuidade (`cerebro_vivo/` e `.cerebro-vivo/`)

Se houver conflito entre o protocolo antigo de especialista unico e o modo multi-agentes abaixo, prevalece este `AGENTS.md`.

## REGRAS CRITICAS (NUNCA VIOLAR)

- Nunca misturar dados entre empresas
- Sempre usar `empresa_id` em todas as consultas
- Sempre usar UUID como identificador primario de sincronizacao
- Nunca criar codigo monolitico
- Nunca burlar validacao ou autenticacao
- Nunca armazenar dados com mais de 14 meses nas tabelas principais

## MODO OFICIAL MULTI-AGENTES

Todo trabalho neste repositorio deve operar em modo multi-agentes coordenado.

### Estrutura obrigatoria de atuacao

- Agente lider: responsavel por consolidar contexto, plano, execucao e validacao final
- Agentes especialistas: contribuem por dominio sem romper as regras criticas
- Revisor final: confirma isolamento multi-tenant, retencao, seguranca e modularidade antes de concluir

### Papeis minimos por tipo de demanda

- Seguranca e autenticacao: `Security Specialist` como participante obrigatorio
- Dados, observabilidade, logs, retencao ou migracoes: `DBA` e/ou `Data/Logs Specialist` como participantes obrigatorios
- Escopo, impacto no usuario, priorizacao e continuidade: `Project Manager` como participante obrigatorio
- API, regras de negocio e sincronizacao: `Backend Engineer` e/ou `API Specialist`
- Estrutura global e modularidade: `Software Architect`
- Validacao: `QA Engineer`

### Regra de decisao

- Toda resposta deve explicitar o agente lider e os especialistas secundarios relevantes
- A execucao deve refletir colaboracao real entre papeis, mesmo quando uma unica pessoa ou IA operacionaliza o trabalho
- Decisoes com impacto em multi-tenant, retencao, autenticacao, auditoria ou logs exigem revisao cruzada entre pelo menos dois papeis
- Nenhum especialista pode autorizar excecao contra as regras criticas

### Formato recomendado de resposta

Usar o [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md) como base, adaptando o cabecalho para multi-agentes quando houver mais de um papel envolvido.

Formato recomendado:

```text
[Agente lider: Nome da Area]
[Especialistas de apoio: Area 1, Area 2]

Analise:
(Explique o problema de forma tecnica)

Solucao:
(Descreva a solucao profissional)

Implementacao:
(Codigo, estrutura ou passo a passo)

Boas praticas aplicadas:
(Listar quais praticas foram seguidas)
```

## REGRAS DE ARQUITETURA

- Seguir arquitetura em camadas:
  - API (rotas)
  - Services (logica de negocio)
  - Repositories (acesso a banco)
  - Models (ORM)
  - Schemas (validacao)

- Cada camada deve ter responsabilidade unica
- Nao acessar o banco diretamente pela camada de API

## REGRAS DE BANCO DE DADOS

- Multi-tenant via coluna:
  - `empresa_id` (indexada)

- Campos obrigatorios em todas as tabelas de sync:
  - `uuid` (identificador global unico)
  - `empresa_id`
  - `data_atualizacao`

- Usar UPSERT em todas as gravacoes

- Usar particionamento por data no PostgreSQL

## POLITICA DE RETENCAO DE DADOS

- Manter apenas 14 meses nas tabelas principais
- Dados antigos devem ser:
  - excluidos OU
  - movidos para tabelas de arquivo

- Preferir remocao de particao em vez de DELETE

## REGRAS DE SEGURANCA

- Todos os endpoints exigem API KEY
- Validar `empresa_id` com a API KEY
- Prevenir SQL injection
- Validar todas as entradas

## PADRAO DE CODIGO

- Usar Python
- Usar FastAPI
- Usar SQLAlchemy ORM

Regras:
- Usar nomes claros em ingles quando fizer sentido tecnico
- Evitar abreviacoes
- Preferir funcoes pequenas
- Seguir principios SOLID

## ESTRUTURA DO PROJETO

### Estrutura canonica operacional

As fontes canonicas operacionais deste repositorio sao:

- `/backend`
- `/agent_local`
- `/sync-admin`
- `/infra`

Essas pastas definem a operacao principal, a arquitetura alvo e a governanca oficial do produto.

### Estrutura de compatibilidade e onboarding

As seguintes trilhas permanecem no workspace como camadas de compatibilidade, transicao ou onboarding:

- `backend/src`
- `frontend`
- `database`
- `devops`
- `docker-compose.yml` na raiz

Regras para convivencia:
- artefatos de compatibilidade nao substituem a governanca das fontes canonicas operacionais;
- qualquer ajuste nessas camadas deve preservar isolamento por `empresa_id`, autenticacao, UUID de sincronizacao, modularidade e retencao maxima de 14 meses;
- em caso de divergencia estrutural, prevalece a decisao registrada para `backend/`, `agent_local/`, `sync-admin/` e `infra/`.

/backend
    /api
    /services
    /repositories
    /models
    /schemas
    /config
    /utils

/agent_local
    /db
    /sync
    /config

## MEMORIA OPERACIONAL E CONTINUIDADE

O projeto passa a conviver com duas camadas complementares de memoria:

- `.cerebro-vivo/`: base operacional local-first, historica e detalhada
- `cerebro_vivo/`: camada top-level, legivel e curada para coordenacao multi-agentes, continuidade rapida e decisao executiva

Regras de coexistencia:
- Nao duplicar arbitrariamente fatos; sempre referenciar a fonte canonica na `.cerebro-vivo/` quando aplicavel
- Usar `cerebro_vivo/estado_atual.md` como resumo executivo de retomada
- Usar `cerebro_vivo/historico_decisoes.md` para registrar decisoes consolidadas e seus vinculos com a base existente
- Usar `cerebro_vivo/memoria_projeto.json` como espelho leve de estado, nunca como substituto unico da memoria operacional detalhada

## REGRAS DE SINCRONIZACAO

- Enviar apenas registros novos ou atualizados
- Usar `data_atualizacao` para filtragem
- Processar em lote, evitando chamadas unitarias

## REGRAS DE TESTE

- Sempre criar testes unitarios
- Validar:
  - isolamento multi-tenant
  - comportamento de upsert
  - regras de retencao

## ANTES DE FINALIZAR QUALQUER TAREFA

O agente deve:

1. Validar conformidade com a arquitetura
2. Verificar isolamento multi-tenant
3. Garantir ausencia de valores hardcoded
4. Garantir que a regra de retencao foi respeitada
5. Garantir que o codigo esta modular
6. Confirmar que o modo multi-agentes foi aplicado de forma coerente com a demanda
7. Atualizar a memoria executiva quando a tarefa alterar contexto relevante de continuidade

## PROTOCOLO DE RESPOSTA

Seguir [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md) como modelo operacional para formato de resposta e execucao senior, ajustando a selecao de papel para o modo multi-agentes definido neste arquivo.
