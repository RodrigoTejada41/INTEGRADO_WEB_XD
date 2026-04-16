# Especificação de Sincronização

> Esta especificação deve ser interpretada junto com [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) quando usada por um agente neste repositório.

## Estratégia

- Incremental sync
- Based on data_atualizacao

## Frequência

- Every 15 minutes

## Regras

- No duplicate data
- Use UUID
- Use UPSERT

## Resolução de conflitos

- Latest data wins
