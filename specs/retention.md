# Data Retention Policy

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
