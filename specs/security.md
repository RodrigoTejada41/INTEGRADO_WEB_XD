# Especificação de Segurança

> Leia esta especificação junto com [`CEREBRO_VIVO.md`](../CEREBRO_VIVO.md) e [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md).

## Autenticação

- API key por empresa

## Validação

- Validação de entrada obrigatória
- Rejeitar dados malformados

## Isolamento

- `empresa_id` deve ser aplicado em todas as consultas

## Logging

- Registrar todas as operações de sync
