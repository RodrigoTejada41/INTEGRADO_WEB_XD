# Arquitetura

> Esta especificação deve ser interpretada junto com [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) quando usada por um agente neste repositório.

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
