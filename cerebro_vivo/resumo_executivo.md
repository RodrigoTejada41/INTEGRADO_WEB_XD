# Resumo Executivo do Projeto

## O que o projeto e

Plataforma comercial de sincronizacao de dados multi-tenant.

Arquitetura-alvo:
- agentes locais em MariaDB;
- API central em FastAPI;
- banco central em PostgreSQL;
- painel admin para operacao, logs, conexoes e sincronizacao;
- relatorios operacionais em tempo real.

## Como o projeto deve ser

- modular;
- escalavel;
- seguro;
- com arquitetura em camadas;
- com separacao clara entre API, services, repositories, models e schemas;
- com autenticacao forte e revogacao de acesso;
- com auditoria obrigatoria;
- com testes obrigatorios;
- com documentacao obrigatoria;
- com memoria persistente e checkpoint local-first.

## Regras criticas

1. Nunca misturar dados entre empresas.
2. Sempre usar `empresa_id` em todas as consultas.
3. Sempre usar UUID como identificador primario de sincronizacao.
4. Nunca criar codigo monolitico.
5. Nunca burlar validacao ou autenticacao.
6. Nunca armazenar dados com mais de 14 meses nas tabelas principais.

## Operacao esperada

- sincronizacao periodica;
- isolamento por tenant;
- matriz e filiais com escopo separado;
- rotas admin e cliente separadas;
- deploy pronto para VPS Linux;
- deploy automatizado via GitHub Actions;
- runbook de producao unico;
- checkpoint de continuidade sempre atualizado.

## Estado atual

- backlog funcional consolidado ate P20;
- producao validada em VPS;
- runbook operacional consolidado em `infra/RUNBOOK_PRODUCAO.md`;
- baseline local validado com a suite completa.

## Proxima direcao

Priorizar o backlog pos-P20 com foco em:
- seguranca operacional;
- continuidade;
- health/readiness;
- rotina de deploy e recuperacao;
- reducao de drift local.
