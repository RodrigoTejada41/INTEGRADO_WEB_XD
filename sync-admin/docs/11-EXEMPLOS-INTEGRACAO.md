# Exemplos de Integracao

## cURL - envio de lote
```bash
curl -X POST "http://localhost:8080/api/sync-data" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sync-key-change-me" \
  -d '{
    "external_batch_id": "BATCH-EX-001",
    "company_code": "EMP01",
    "branch_code": "FIL01",
    "terminal_code": "PDV01",
    "records": [
      {
        "record_key": "DOC-1001",
        "record_type": "sale",
        "payload": {"total": 123.45}
      }
    ]
  }'
```

## PowerShell - envio de lote
```powershell
$body = @{
  external_batch_id = 'BATCH-EX-001'
  company_code = 'EMP01'
  branch_code = 'FIL01'
  terminal_code = 'PDV01'
  records = @(
    @{
      record_key = 'DOC-1001'
      record_type = 'sale'
      payload = @{ total = 123.45 }
    }
  )
} | ConvertTo-Json -Depth 6

Invoke-WebRequest -Uri 'http://localhost:8080/api/sync-data' -Method Post -ContentType 'application/json' -Headers @{ 'X-API-Key'='sync-key-change-me' } -Body $body
```
