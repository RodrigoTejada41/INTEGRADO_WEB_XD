# Visão Geral da Arquitetura

## Fluxo principal
`Pasta de conhecimento -> Ingestão -> Engenharia reversa -> Transformação -> Persistência -> API -> Relatórios`

## Integrações obrigatórias
- Obsidian: notas Markdown geradas em `obsidian-vault/03-datasets`
- Nexus: manifestos versionados gerados em `nexus-manifests/snapshots`

## Fronteiras dos serviços
- Ingestão: descoberta de arquivos e deduplicação
- Engenharia reversa: inferência dinâmica de estrutura
- Transformação: normalização e versionamento semântico
- Persistência: publicação de artefatos e documentação legível por pessoas
- API: acesso seguro e versionado aos dados

## Base de segurança
- Token Bearer nos endpoints da API (MVP)
- Tabela de eventos de auditoria pronta para expansão
- Separação por processo de serviço e contratos de evento explícitos

## Base de observabilidade
- Cada serviço grava jobs de estágio em `processing_jobs`
- Estado da fila de eventos rastreado em `event_queue`
- Evolução para logs estruturados prevista no próximo incremento
