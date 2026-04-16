# Architecture Overview

## Core flow
`Knowledge folder -> Ingestion -> Reverse Engineering -> Transformation -> Persistence -> API -> Reporting`

## Mandatory integrations
- Obsidian: generated markdown notes in `obsidian-vault/03-datasets`
- Nexus: generated versioned manifests in `nexus-manifests/snapshots`

## Services boundaries
- Ingestion: file discovery and deduplication
- Reverse Engineering: dynamic structure inference
- Transformation: normalization and semantic versioning
- Persistence: artifact publishing and human-readable documentation
- API: secure versioned data access

## Security baseline
- Bearer token on API endpoints (MVP)
- Audit events table ready for expansion
- Separation by service process and explicit event contracts

## Observability baseline
- Each service writes stage jobs in `processing_jobs`
- Event queue state tracked in `event_queue`
- Structured log evolution planned in next increment
