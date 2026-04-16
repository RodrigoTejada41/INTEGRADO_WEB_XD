# Sync Specification

> This specification must be interpreted through [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) when used by an agent in this repository.

## Strategy

- Incremental sync
- Based on data_atualizacao

## Frequency

- Every 15 minutes

## Rules

- No duplicate data
- Use UUID
- Use UPSERT

## Conflict Resolution

- Latest data wins
