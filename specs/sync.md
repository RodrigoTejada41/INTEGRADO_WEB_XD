# Especificação de Sincronização

> Leia esta especificação junto com [`CEREBRO_VIVO.md`](../CEREBRO_VIVO.md) e [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md).

## Estratégia

- Sincronização incremental
- Baseada em `data_atualizacao`

## Frequência

- A cada 15 minutos

## Regras

- Não duplicar dados
- Usar UUID
- Usar UPSERT

## Resolução de conflitos

- O dado mais recente prevalece
