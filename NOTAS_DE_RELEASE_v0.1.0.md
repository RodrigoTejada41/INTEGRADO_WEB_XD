# Notas de Release - v0.1.0

> Estas notas de release seguem o protocolo operacional definido em [`PROTOCOLO_ESPECIALISTAS.md`](PROTOCOLO_ESPECIALISTAS.md).

## Resumo
Base inicial pronta para produção da plataforma de sincronização de dados.

## Destaques
- Arquitetura modular de API e agente.
- Sincronização incremental com upsert baseado em `uuid`.
- Validação multi-tenant com `empresa_id`.
- Política de retenção limitada a 14 meses.
- Painel administrativo com login, dashboard, registros, histórico e configurações.
- Provisionamento de tenant e rotação de chave pelo painel.
- Health checks, métricas e testes automatizados.

## Validação
- Suíte automatizada: `8 passed`
- Tag de release: `v0.1.0`

## Observações
- Esta release estabelece a base para a próxima fase comercial.
- A linha de trabalho seguinte foca em isolamento multiempresa mais profundo, exports mais ricos e monitoramento avançado.
