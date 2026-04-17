# Especificação de Segurança

> Esta especificação deve ser interpretada junto com [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) quando usada por um agente neste repositório.

## Autenticação

- API KEY por empresa

## Validação

- Validação de entrada obrigatória
- Rejeitar dados malformados

## Isolamento

- `empresa_id` deve ser aplicado em todas as consultas

## Logging

- Registrar todas as operações de sync
