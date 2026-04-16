# Data Retention Policy

> This specification must be interpreted through [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) when used by an agent in this repository.

## Rule

- Keep only 14 months of data

## Strategy

- Partition by date
- Drop old partitions

## Alternative

- Move to archive tables

## Execution

- Daily scheduled job

## Constraints

- Never query data older than 14 months
