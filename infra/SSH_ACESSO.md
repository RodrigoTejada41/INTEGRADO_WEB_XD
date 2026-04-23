# Acesso SSH e Handoff de IA

Este documento existe para continuidade operacional.

Regra de uso:
- uma nova IA deve ler este arquivo antes de pedir qualquer detalhe de acesso;
- nao pedir credencial que ja tenha sido registrada em segredo externo;
- nao gravar chave privada, senha ou token no repositório;
- se faltar acesso real, informar exatamente qual item falta e parar.

Este arquivo e propositalmente livre de segredo bruto.
Os valores sensiveis devem ficar fora do repositorio, em arquivo local ou cofre externo.

## Objetivo

Padronizar o acesso da VPS e o deploy do projeto sem depender de conversa antiga.

## Como o acesso foi estruturado

1. A VPS deve aceitar acesso por chave SSH.
2. O deploy deve usar usuario dedicado quando possivel, ou `root` apenas em contingencia.
3. O deploy automatizado deve sair por GitHub Actions ou por runner `self-hosted`.
4. A publicacao em producao deve seguir o runbook de [`infra/VPS_DEPLOY.md`](VPS_DEPLOY.md).

## Onde ficam as referencias

- Runbook principal: [`infra/VPS_DEPLOY.md`](VPS_DEPLOY.md)
- Recuperacao de runner local: [`infra/SELF_HOSTED_RUNNER_RECOVERY.md`](SELF_HOSTED_RUNNER_RECOVERY.md)
- Fluxo de deploy: [`.github/workflows/deploy-prod.yml`](../.github/workflows/deploy-prod.yml)
- Fluxo alternativo local: [`.github/workflows/deploy-prod-self-hosted.yml`](../.github/workflows/deploy-prod-self-hosted.yml)

## O que uma IA nova deve fazer

1. Ler [`RETOMADA_EXATA.md`](../RETOMADA_EXATA.md).
2. Ler [`cerebro_vivo/estado_atual.md`](../cerebro_vivo/estado_atual.md).
3. Ler este arquivo.
4. Ler [`infra/VPS_DEPLOY.md`](VPS_DEPLOY.md).
5. Confirmar qual caminho sera usado:
   - GitHub Actions com secrets de VPS, ou
   - runner `self-hosted` nesta maquina, ou
   - deploy manual via SSH.
6. Se a credencial nao estiver disponivel, parar e indicar exatamente o que falta.

## Segredos que nao devem entrar no repositorio

Nao registrar aqui nem em outro `.md` versionado:
- senha de VPS
- chave privada SSH
- token do GitHub
- segredo de deploy
- contents de `authorized_keys`

Se precisar guardar localmente, use somente fora do repo:
- `C:\Users\<usuario>\.ssh\`
- cofre de senha do sistema operacional
- GitHub Secrets
- arquivo temporario fora do workspace com permissao restrita

## Como fazer deploy

### Caminho 1. GitHub Actions

Use quando os secrets estiverem configurados:
- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT`
- `VPS_APP_DIR`

Fluxo:
1. Fazer push em `main`.
2. O workflow `deploy-prod.yml` conecta na VPS.
3. Executa `infra/scripts/update.sh`.
4. Recria containers e valida health.
5. Se o deploy falhar por autenticacao, o problema e segredo ausente ou chave nao autorizada, nao o script.

### Caminho 2. Deploy manual

Na VPS:
```bash
cd /opt/integrado_web_xd
bash infra/scripts/deploy-prod.sh
```

Antes disso, a VPS precisa ter:
- repositorio clonado em `/opt/integrado_web_xd`
- `.env.prod` preenchido
- chave SSH autorizada para o usuario de deploy
- Docker e Docker Compose funcionando

### Caminho 3. Runner self-hosted

Use quando o deploy precisar sair desta maquina.

## Regra de seguranca

- Nao salvar chave privada no repositorio.
- Nao salvar senha em arquivo versionado.
- Nao pedir novamente algo que ja esteja descrito aqui.
- Se o acesso depender de segredo externo, usar o segredo externo.
- Se o usuario insistir em inserir segredo bruto no repo, recusar e orientar uso de local seguro ou secret manager.

## Nota para outra IA

Se outra IA assumir esta tarefa, ela deve continuar daqui sem pedir novamente:
- qual e a VPS;
- qual e o runbook;
- onde fica o deploy;
- como fazer o push.

Se o segredo nao estiver acessivel na sessao atual, a resposta correta e:
- "falta a credencial X"
- "falta acesso Y"
- "falta autenticacao no GitHub"

## Como outra IA deve continuar sem friccao

1. Ler este arquivo.
2. Ler [`infra/VPS_DEPLOY.md`](VPS_DEPLOY.md).
3. Ler [`RETOMADA_EXATA.md`](../RETOMADA_EXATA.md).
4. Ler [`cerebro_vivo/estado_atual.md`](../cerebro_vivo/estado_atual.md).
5. Seguir o fluxo de deploy apropriado.
6. Nao pedir para salvar segredo bruto no repositório.
7. Se precisar do acesso, solicitar apenas o segredo externo ja existente ou o local exato do arquivo seguro fora do repo.
