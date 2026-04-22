# Especificação de Banco de Dados

> Leia esta especificação junto com [`CEREBRO_VIVO.md`](../CEREBRO_VIVO.md) e [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md).

## Motor

- PostgreSQL (central)
- MariaDB (local)

## Multi-tenant

Todas as tabelas devem incluir:

- `empresa_id` indexado

## Campos obrigatórios

- `uuid` único
- `data_atualizacao`

## Índices

- `empresa_id`
- `uuid`
- `data`

## Particionamento

- Particionamento mensal
- Baseado em campo de data

## Exemplo de tabela

`vendas`:
- `id`
- `uuid`
- `empresa_id`
- `produto`
- `valor`
- `data`
- `data_atualizacao`
