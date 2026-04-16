# Política de Retenção de Dados

> Esta especificação deve ser interpretada junto com [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) quando usada por um agente neste repositório.

## Regra

- Keep only 14 months of data

## Estratégia

- Partition by date
- Drop old partitions

## Alternativa

- Move to archive tables

## Execução

- Daily scheduled job

## Restrições

- Never query data older than 14 months
