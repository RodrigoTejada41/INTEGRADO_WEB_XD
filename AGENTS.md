# AGENTS.md

## PROJECT OVERVIEW

This project is a multi-tenant data synchronization platform.

Architecture:
- Local agents (MariaDB)
- Central API (FastAPI)
- Central database (PostgreSQL)

Main goals:
- Sync data every 15 minutes
- Ensure strict data isolation per company
- Maintain only 14 months of data in primary database

## CRITICAL RULES (NEVER VIOLATE)

- NEVER mix data between companies
- ALWAYS use empresa_id in all queries
- ALWAYS use UUID as primary sync identifier
- NEVER create monolithic code
- NEVER bypass validation or authentication
- NEVER store data older than 14 months in main tables

## ARCHITECTURE RULES

- Follow layered architecture:
  - API (routes)
  - Services (business logic)
  - Repositories (database access)
  - Models (ORM)
  - Schemas (validation)

- Each layer must have a single responsibility
- No direct DB access from API layer

## DATABASE RULES

- Multi-tenant via column:
  - empresa_id (indexed)

- Required fields in all sync tables:
  - uuid (unique global id)
  - empresa_id
  - data_atualizacao

- Use UPSERT for all writes

- Use PostgreSQL partitioning by date

## DATA RETENTION POLICY

- Keep only 14 months in main tables
- Older data must be:
  - deleted OR
  - moved to archive tables

- Prefer partition drop instead of DELETE

## SECURITY RULES

- All endpoints require API KEY
- Validate empresa_id against API KEY
- Prevent SQL injection
- Validate all inputs

## CODE STYLE

- Use Python
- Use FastAPI
- Use SQLAlchemy ORM

Rules:
- Use clear naming (English)
- Avoid abbreviations
- Prefer small functions
- Follow SOLID principles

## PROJECT STRUCTURE

/backend
    /api
    /services
    /repositories
    /models
    /schemas
    /config
    /utils

/agent_local
    /db
    /sync
    /config

## SYNC RULES

- Only send new or updated records
- Use data_atualizacao for filtering
- Batch requests (avoid single record calls)

## TESTING RULES

- Always create unit tests
- Validate:
  - multi-tenant isolation
  - upsert behavior
  - retention rules

## BEFORE FINISHING ANY TASK

The agent must:

1. Validate architecture compliance
2. Check multi-tenant isolation
3. Ensure no hardcoded values
4. Ensure retention rule is respected
5. Ensure code is modular
