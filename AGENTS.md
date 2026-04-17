# AGENTS.md

## VISÃO GERAL DO PROJETO

Este projeto é uma plataforma de sincronização de dados multi-tenant.

Arquitetura:
- Agentes locais (MariaDB)
- API central (FastAPI)
- Banco central (PostgreSQL)

Objetivos principais:
- Sincronizar dados a cada 15 minutos
- Garantir isolamento rigoroso por empresa
- Manter apenas 14 meses de dados no banco principal

## REGRAS CRÍTICAS (NUNCA VIOLAR)

- Nunca misturar dados entre empresas
- Sempre usar `empresa_id` em todas as consultas
- Sempre usar UUID como identificador primário de sincronização
- Nunca criar código monolítico
- Nunca burlar validação ou autenticação
- Nunca armazenar dados com mais de 14 meses nas tabelas principais

## REGRAS DE ARQUITETURA

- Seguir arquitetura em camadas:
  - API (rotas)
  - Services (lógica de negócio)
  - Repositories (acesso a banco)
  - Models (ORM)
  - Schemas (validação)

- Cada camada deve ter responsabilidade única
- Não acessar o banco diretamente pela camada de API

## REGRAS DE BANCO DE DADOS

- Multi-tenant via coluna:
  - `empresa_id` (indexada)

- Campos obrigatórios em todas as tabelas de sync:
  - `uuid` (identificador global único)
  - `empresa_id`
  - `data_atualizacao`

- Usar UPSERT em todas as gravações

- Usar particionamento por data no PostgreSQL

## POLÍTICA DE RETENÇÃO DE DADOS

- Manter apenas 14 meses nas tabelas principais
- Dados antigos devem ser:
  - excluídos OU
  - movidos para tabelas de arquivo

- Preferir remoção de partição em vez de DELETE

## REGRAS DE SEGURANÇA

- Todos os endpoints exigem API KEY
- Validar `empresa_id` com a API KEY
- Prevenir SQL injection
- Validar todas as entradas

## PADRÃO DE CÓDIGO

- Usar Python
- Usar FastAPI
- Usar SQLAlchemy ORM

Regras:
- Usar nomes claros em inglês quando fizer sentido técnico
- Evitar abreviações
- Preferir funções pequenas
- Seguir princípios SOLID

## ESTRUTURA DO PROJETO

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

## REGRAS DE SINCRONIZAÇÃO

- Enviar apenas registros novos ou atualizados
- Usar `data_atualizacao` para filtragem
- Processar em lote, evitando chamadas unitárias

## REGRAS DE TESTE

- Sempre criar testes unitários
- Validar:
  - isolamento multi-tenant
  - comportamento de upsert
  - regras de retenção

## ANTES DE FINALIZAR QUALQUER TAREFA

O agente deve:

1. Validar conformidade com a arquitetura
2. Verificar isolamento multi-tenant
3. Garantir ausência de valores hardcoded
4. Garantir que a regra de retenção foi respeitada
5. Garantir que o código está modular

## PROTOCOLO DE RESPOSTA

Seguir [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md) como modelo operacional para seleção de papel, formato de resposta e execução sênior.
