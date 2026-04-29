# Autorizacoes operacionais

Atualizado em: 2026-04-29

## Objetivo

Registrar autorizacoes recorrentes dadas pelo responsavel do projeto para reduzir interrupcoes em operacoes tecnicas previsiveis.

## Escopo autorizado

Para o projeto `INTEGRADO_WEB_XD`, o operador autorizou executar sem nova confirmacao manual, quando tecnicamente necessario:

- consultar estado do Git local e remoto;
- executar testes automatizados;
- criar commit das alteracoes implementadas;
- fazer push da branch de trabalho para o GitHub;
- acessar a VPS de producao via SSH usando a chave configurada;
- consultar estado da VPS antes do deploy;
- preservar alteracoes locais da VPS antes de atualizar codigo;
- atualizar a branch de deploy na VPS;
- executar `infra/scripts/deploy-prod.sh`;
- executar migrations via `scripts/db_migrate.py`;
- validar containers Docker;
- validar endpoints de health/readiness;
- validar schema do banco apos migration.

## Limites

Mesmo com esta autorizacao, nao fazer sem avaliacao tecnica:

- apagar backups;
- apagar certificados;
- remover dados de banco;
- executar `git reset --hard` sem backup previo;
- sobrescrever alteracoes manuais da VPS sem preservar patch/stash;
- expor tokens, senhas, chaves privadas ou conteudo de `.env`.

## Procedimento seguro para deploy

1. Confirmar branch e commit local.
2. Confirmar que o commit foi enviado ao GitHub.
3. Verificar estado da VPS.
4. Se a VPS estiver suja, preservar antes:
   - patch de diff;
   - stash de arquivos rastreados;
   - backup de arquivos nao rastreados relevantes.
5. Fazer checkout da branch autorizada.
6. Executar `bash infra/scripts/deploy-prod.sh`.
7. Validar:
   - containers saudaveis;
   - migration aplicada;
   - endpoints publicos respondendo;
   - rotas funcionais criticas.

## Estado desta autorizacao

Autorizacao registrada a pedido do usuario durante o deploy dos relatorios comerciais/financeiros.

Esta documentacao nao substitui regras de seguranca do ambiente de execucao. Se o sandbox exigir aprovacao tecnica, a aprovacao ainda pode aparecer, mas este arquivo deve ser usado como referencia operacional para decidir rapidamente.
