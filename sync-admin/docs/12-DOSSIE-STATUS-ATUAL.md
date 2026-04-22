# Dossie de Status Atual

## Description
Resumo do estado atual do `sync-admin` para retomada rapida.

## Structure
- [`modules/README.md`](./modules/README.md)
- [`../CHANGELOG.md`](../CHANGELOG.md)
- [`../../RETOMADA_EXATA.md`](../../RETOMADA_EXATA.md)

## Integrations
- Painel web (`dashboard`, `records`, `history`, `settings`)
- API de controle do backend de sync
- Base local-first (`.cerebro-vivo`)

## Flow
1. Ler `RETOMADA_EXATA.md`.
2. Confirmar `py -3 -m pytest -q`.
3. Continuar a partir do proximo item apos `P14` (`P15`).

## Critical Points
- Manter isolamento por `empresa_id`.
- Nao remover filtros por empresa/filial/terminal no painel.
- Nao quebrar exportacoes `CSV/XLSX/PDF/Markdown`.

## Tests
- Baseline atual: `20 passed`.
