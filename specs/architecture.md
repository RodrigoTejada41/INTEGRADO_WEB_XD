# Arquitetura

> Leia esta especificação junto com [`CEREBRO_VIVO.md`](../CEREBRO_VIVO.md) e [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md).

## Visão geral

Sistema composto por:

1. Agente local
2. API central
3. Banco central

## Fluxo

Banco local -> Agente -> API -> PostgreSQL -> Painel web

## Princípios

- Arquitetura modular
- Escalável
- API sem estado
- Isolamento multi-tenant
