# Especificação de Banco de Dados

> Esta especificação deve ser interpretada junto com [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) quando usada por um agente neste repositório.

## Motor

- PostgreSQL (central)
- MariaDB (local)

## Multi-tenant

Todas as tabelas devem incluir:

- empresa_id (indexed)

## Campos obrigatórios

- uuid (unique)
- data_atualizacao

## Índices

- empresa_id
- uuid
- data

## Particionamento

- Partition by month
- Based on date field

## Exemplo de tabela

vendas:
- id
- uuid
- empresa_id
- produto
- valor
- data
- data_atualizacao
