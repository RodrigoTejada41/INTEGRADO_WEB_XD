# Architecture

> This specification must be interpreted through [`PROTOCOLO_ESPECIALISTAS.md`](../PROTOCOLO_ESPECIALISTAS.md) when used by an agent in this repository.

## Overview

System composed of:

1. Local Agent
2. Central API
3. Central Database

## Flow

Local DB -> Agent -> API -> PostgreSQL -> Web Panel

## Principles

- Modular architecture
- Scalable
- Stateless API
- Multi-tenant isolation
