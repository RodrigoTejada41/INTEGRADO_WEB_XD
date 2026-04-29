# Relatorios comerciais e financeiros

## Objetivo

Modulo de BI para consultar vendas e faturamento por periodo, horario, produto, familia, categoria, pagamento, terminal, operador, cliente e status.

## Rotas backend

Todas exigem `X-Admin-Token`.

- `GET /admin/tenants/{empresa_id}/reports/overview`
- `GET /admin/tenants/{empresa_id}/reports/daily-sales`
- `GET /admin/tenants/{empresa_id}/reports/top-products`
- `GET /admin/tenants/{empresa_id}/reports/breakdown`
- `GET /admin/tenants/{empresa_id}/reports/recent-sales`
- `GET /admin/tenants/{empresa_id}/reports/branches`

## Filtros aceitos

- `start_date`
- `end_date`
- `start_time`
- `end_time`
- `branch_code`
- `terminal_code`
- `category`
- `product`
- `product_code`
- `family`
- `payment_method`
- `card_brand`
- `status_filter`
- `canceled`
- `operator`
- `customer`
- `limit`

## Agrupamentos aceitos

Usar em `reports/breakdown?group_by=...`.

- `tipo_venda`
- `forma_pagamento`
- `bandeira_cartao`
- `familia_produto`
- `categoria_produto`
- `terminal_code`
- `branch_code`
- `operador`
- `status_venda`
- `cliente`
- `codigo_produto_local`

## Exportacao

As exportacoes do `sync-admin` respeitam os filtros da tela.

- `GET /reports/export.csv`
- `GET /reports/export.xlsx`
- `GET /reports/export.pdf`
- `GET /client/reports/export.csv`
- `GET /client/reports/export.xlsx`
- `GET /client/reports/export.pdf`

CSV usa `;` para compatibilidade com Excel em PT-BR.

## Interface cliente

A tela do cliente usa navegação em duas etapas:

1. Dashboard principal:
   - KPIs resumidos;
   - gráficos essenciais;
   - ranking curto;
   - atalhos de relatório.
2. Visualização dedicada:
   - aberta por `report_view`;
   - mostra somente o relatório selecionado;
   - mantém filtros e exportações do contexto aplicado.

Valores aceitos em `report_view`:

- `dashboard`
- `daily_revenue`
- `payments`
- `products`
- `families`
- `terminals`
- `sales`

Exemplo:

```text
/client/reports?report_view=daily_revenue&period_preset=today
```

Esse fluxo evita concentrar todos os gráficos, filtros e tabelas em uma única tela.

## Produto local

O campo `codigo_produto_local` e preservado como referencia principal do produto.

Tabela de apoio:

- `produto_de_para`

Chave unica:

- `empresa_id`
- `codigo_produto_local`

O DE/PARA nao substitui o codigo local. Ele apenas permite exibir equivalente web quando existir mapeamento.

## Rotas administrativas DE/PARA

Rotas protegidas por `X-Admin-Token` e auditadas:

- `GET /admin/tenants/{empresa_id}/produto-de-para`
- `POST /admin/tenants/{empresa_id}/produto-de-para`
- `PUT /admin/tenants/{empresa_id}/produto-de-para/{mapping_id}`
- `DELETE /admin/tenants/{empresa_id}/produto-de-para/{mapping_id}`
- `GET /admin/tenants/{empresa_id}/produto-de-para/unmapped`

Regras:

- `cnpj` deve ser igual ao `empresa_id` informado na rota.
- `codigo_produto_local` e unico por empresa.
- `POST` faz upsert por `empresa_id + codigo_produto_local`.
- produtos sem DE/PARA continuam aparecendo nos relatorios com dados locais.
- a tela `/settings` permite cadastrar, editar, remover e listar produtos pendentes de mapeamento.

## Referencia XD Software

Arquivo local usado como referencia:

```text
TABELAS DO BANCO XD/REFERENCIA TABELAS BD XD SOFTWARE.xlsx
```

Tabelas XD relevantes para carga local MariaDB:

- `salesdocumentsreportview`
- `Documentsbodys`
- `Documentsheaders`
- `Invoicepaymentdetails`
- `Xconfigpaymenttypes`
- `Itemsgroups`
- `Items`
- `Entities`

Ordem de decisao do agente local:

1. Usar `salesdocumentsreportview` quando existir.
2. Usar fallback `Documentsbodys + Documentsheaders` quando a view nao existir.
3. Enriquecer pagamento via `Invoicepaymentdetails + Xconfigpaymenttypes` quando existir.
4. Enriquecer familia via `Itemsgroups` quando existir.
5. Preservar `ItemKeyId` como `codigo_produto_local`.

## Rotas de diagnostico XD local

Rotas no `sync-admin`, protegidas por permissao de configuracao:

- `GET /settings/xd-mapping`
- `GET /settings/xd-mapping/routes`

Uso:

- validar quais tabelas XD existem no MariaDB local;
- confirmar se a origem ativa e `salesdocumentsreportview` ou `Documentsbodys + Documentsheaders`;
- verificar as colunas detectadas sem expor senha do banco.

## Exemplos

Faturamento do dia:

```text
/admin/tenants/12345678000199/reports/overview?start_date=2026-04-29&end_date=2026-04-29
```

Vendas do terminal 02 das 08:00 as 12:00:

```text
/admin/tenants/12345678000199/reports/recent-sales?terminal_code=02&start_time=08:00&end_time=12:00
```

Faturamento por forma de pagamento:

```text
/admin/tenants/12345678000199/reports/breakdown?group_by=forma_pagamento
```

Produtos por codigo local:

```text
/admin/tenants/12345678000199/reports/top-products?product_code=789001
```

Cancelamentos:

```text
/admin/tenants/12345678000199/reports/recent-sales?canceled=true
```
