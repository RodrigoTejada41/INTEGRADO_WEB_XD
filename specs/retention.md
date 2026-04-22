# Política de Retenção de Dados

> Leia esta especificação junto com [`CEREBRO_VIVO.md`](../CEREBRO_VIVO.md) e [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md).

## Regra

- Manter apenas 14 meses de dados

## Estratégia

- Particionar por data
- Remover partições antigas

## Alternativa

- Mover para tabelas de arquivo

## Execução

- Job agendado diário

## Restrições

- Nunca consultar dados com mais de 14 meses nas tabelas principais
