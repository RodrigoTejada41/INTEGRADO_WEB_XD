# Especificação da API

> Leia esta especificação junto com [`CEREBRO_VIVO.md`](../CEREBRO_VIVO.md) e [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md).

## Autenticação

- API key obrigatória

## Endpoint

`POST /sync`

## Requisição

```json
{
  "empresa_id": "string",
  "data": []
}
```

## Regras

- Validar API key
- Validar `empresa_id`
- Rejeitar dados inválidos
- Processar somente em lote

## Resposta

- Sucesso ou detalhes do erro
