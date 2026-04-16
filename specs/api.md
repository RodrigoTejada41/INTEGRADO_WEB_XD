# Especificação da API

> Esta especificação deve ser interpretada junto com [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) quando usada por um agente neste repositório.

## Autenticação

- API KEY required

## Endpoint

POST /sync

## Requisição

```json
{
  "empresa_id": "string",
  "data": []
}
```

## Regras

- Validate API KEY
- Validate empresa_id
- Reject invalid data
- Process batch only

## Resposta

- Success or error details
