# Banco de Dados

## Tecnologia
- PostgreSQL 16 (container `sync_db`).
- ORM SQLAlchemy 2.x.

## Tabelas principais

### `users`
- Autenticacao do painel.
- Campos: `username`, `password_hash`, `role`, `is_active`, `last_login_at`.

### `integration_keys`
- Chaves de integracao para API externa.
- Campos: `key_hash`, `key_prefix`, `is_active`, `last_used_at`.

### `sync_batches`
- Cabecalho de cada envio recebido.
- Campos: `external_batch_id`, `company_code`, `branch_code`, `terminal_code`, `source_ip`, `status`, `records_received`, `payload_hash`, `error_message`, `received_at`.

### `sync_records`
- Registros individuais por lote.
- Campos: `batch_id`, `record_key`, `record_type`, `event_time`, `payload_json`, `created_at`.

## Relacoes
- `sync_batches (1) -> (N) sync_records`.

## Inicializacao
- No startup da API:
  - cria schema (`Base.metadata.create_all`).
  - garante admin inicial.
  - garante chave de integracao inicial.
