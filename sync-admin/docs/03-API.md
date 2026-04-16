# API REST

## Health
### `GET /health`
- Uso: verificacao de disponibilidade.
- Resposta: `{"status":"online"}`.

## Recebimento de sincronizacao
### `POST /api/sync-data`

#### Headers obrigatorios
- `Content-Type: application/json`
- `X-API-Key: <chave_integracao>`

#### Payload
```json
{
  "external_batch_id": "BATCH-20260415-001",
  "company_code": "EMP01",
  "branch_code": "FIL01",
  "terminal_code": "PDV01",
  "sent_at": "2026-04-15T20:00:00Z",
  "records": [
    {
      "record_key": "DOC-1",
      "record_type": "sale",
      "event_time": "2026-04-15T20:00:00Z",
      "payload": {"total": 99.9}
    }
  ]
}
```

#### Regras
- Valida estrutura com Pydantic (`SyncPayloadIn`).
- Valida chave de integracao ativa.
- Registra IP de origem.
- Persiste lote e registros.

#### Resposta de sucesso
```json
{
  "status": "ok",
  "batch_id": 123,
  "records_received": 1,
  "message": "Data received and stored successfully"
}
```

#### Erros comuns
- `401`: sem `X-API-Key` ou chave invalida.
- `422`: payload invalido.
- `500`: erro interno de ingestao.
