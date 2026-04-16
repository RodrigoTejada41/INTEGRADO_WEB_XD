# Database Specification

## Engine

- PostgreSQL (central)
- MariaDB (local)

## Multi-tenant

All tables must include:

- empresa_id (indexed)

## Required Fields

- uuid (unique)
- data_atualizacao

## Indexes

- empresa_id
- uuid
- data

## Partitioning

- Partition by month
- Based on date field

## Example Table

vendas:
- id
- uuid
- empresa_id
- produto
- valor
- data
- data_atualizacao
