# API Specification

> This specification must be interpreted through [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) when used by an agent in this repository.

## Authentication

- API KEY required

## Endpoint

POST /sync

## Request

```json
{
  "empresa_id": "string",
  "data": []
}
```

## Rules

- Validate API KEY
- Validate empresa_id
- Reject invalid data
- Process batch only

## Response

- Success or error details
