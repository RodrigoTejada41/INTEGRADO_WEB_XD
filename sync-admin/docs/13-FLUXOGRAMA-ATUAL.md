# Fluxograma Atual

## Fluxo funcional (alto nível)

```mermaid
flowchart LR
    A[Sistema Local<br/>Extrai MariaDB] -->|POST /api/sync-data<br/>X-API-Key| B[sync_web<br/>Nginx]
    B --> C[sync_api<br/>FastAPI]
    C --> D{Valida API Key<br/>e payload}
    D -->|Invalido| E[Resposta 401/422]
    D -->|Valido| F[Grava sync_batches]
    F --> G[Grava sync_records]
    G --> H[Resposta 200 OK]
    C --> I[(sync_db<br/>PostgreSQL)]
    J[Painel Web] --> B
    B --> C
    C --> K[Painel / Registros / Histórico]
    K --> I
```

## Fluxo de autenticação do painel

```mermaid
flowchart TD
    A[Usuário acessa /login] --> B[Envia usuário/senha]
    B --> C[AuthService valida hash]
    C -->|Falha| D[Retorna login com erro]
    C -->|Sucesso| E[Cria sessão]
    E --> F[Redireciona /dashboard]
    F --> G[Rotas protegidas por require_web_user]
```

## Fluxo de persistência da sincronização

```mermaid
flowchart TD
    A[Payload recebido] --> B[Calcula payload_hash]
    B --> C[Cria SyncBatch]
    C --> D[Itera records]
    D --> E[Cria SyncRecord por item]
    E --> F[Commit]
    F --> G[Retorna batch_id + records_received]
```

## Pontos de controle
- Entrada API: `POST /api/sync-data`
- Saúde: `GET /health`
- Painel: `/login`, `/dashboard`, `/records`, `/history`, `/settings`
- Banco:
  - `sync_batches` para histórico do envio
  - `sync_records` para dados detalhados

## Onde paramos
- Fluxo completo ponta a ponta implementado e validado localmente.
- Ambiente Docker com 3 serviços operacional.
- Documentação de operação e diagnóstico finalizada.

