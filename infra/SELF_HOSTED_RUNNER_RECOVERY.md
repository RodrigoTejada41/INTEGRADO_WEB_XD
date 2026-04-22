# Self-Hosted Runner e Recuperacao

## Objetivo
Usar um runner `self-hosted` nesta maquina para que o deploy automatizado saia do seu computador, e nao da infraestrutura hospedada do GitHub.

Isso permite:
- usar uma chave SSH exclusiva desta maquina
- opcionalmente restringir o acesso por IP/origem
- separar a chave local do secret usado por runners hospedados

## Limite importante
Se o deploy precisa ser executado **somente desta maquina**, o workflow deve rodar em `self-hosted`.

Enquanto o workflow usar `ubuntu-latest`, a conexao sai dos runners do GitHub e a chave nao fica presa a este computador.

## Workflow preparado
Arquivo:
- [deploy-prod-self-hosted.yml](E:\Projetos\INTEGRADO_WEB_XD\.github\workflows\deploy-prod-self-hosted.yml)

Labels esperadas:
- `self-hosted`
- `windows`
- `x64`
- `integrado-web-xd`
- `deploy-local`

## Secrets esperados para o workflow self-hosted
- `VPS_HOST`
- `VPS_USER`
- `VPS_PORT` opcional
- `VPS_APP_DIR` opcional
- `VPS_SSH_KEY_LOCAL`
- `VPS_HOST_PUBLIC_KEY`

Recomendacao:
- manter `VPS_SSH_KEY_LOCAL` separado de qualquer chave usada por runner hospedado
- salvar `VPS_HOST_PUBLIC_KEY` explicitamente para evitar confiar em descoberta dinamica do host

## Como instalar o runner nesta maquina Windows
1. No GitHub, abra:
   `Repository -> Settings -> Actions -> Runners -> New self-hosted runner`
2. Copie:
   - a URL do repositorio
   - o token de registro temporario
3. Execute o script:
```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\install-self-hosted-runner.ps1 `
  -RunnerUrl "https://github.com/RodrigoTejada41/INTEGRADO_WEB_XD" `
  -RegistrationToken "<TOKEN_TEMPORARIO>" `
  -RunnerName "integrado-web-xd-local" `
  -Labels "integrado-web-xd,deploy-local"
```

## Como ligar a chave SSH apenas a esta maquina
1. Gere uma chave dedicada ao deploy local.
```powershell
ssh-keygen -t ed25519 -C "deploy-local-integrado-web-xd" -f $HOME\.ssh\integrado_web_xd_local
```

2. Instale a chave publica na VPS usando o fluxo do usuario `deploy`.
3. Grave a chave privada no secret `VPS_SSH_KEY_LOCAL`.
4. Configure o workflow self-hosted para usar `VPS_USER=deploy`.

Se o seu IP for fixo ou previsivel, voce pode adicionar `DEPLOY_FROM` na VPS para reduzir ainda mais o risco.

## Recuperacao se a maquina for formatada
Formato seguro de retomada:

1. Reinstalar Git, OpenSSH e PowerShell.
2. Clonar o repositorio novamente.
3. Recuperar ou recriar a chave SSH local de deploy.
4. Gerar novo token temporario de registro no GitHub.
5. Reexecutar [install-self-hosted-runner.ps1](E:\Projetos\INTEGRADO_WEB_XD\infra\scripts\install-self-hosted-runner.ps1).
6. Confirmar no GitHub que o runner voltou com as labels corretas.
7. Executar um `workflow_dispatch` de teste.

Se aparecer erro de horario:
- sincronize o relogio do Windows com horario automatico/internet
- execute novamente o script com `-ReplaceExisting`

Exemplo:
```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\install-self-hosted-runner.ps1 `
  -RunnerUrl "https://github.com/RodrigoTejada41/INTEGRADO_WEB_XD" `
  -RegistrationToken "<NOVO_TOKEN_TEMPORARIO>" `
  -RunnerName "integrado-web-xd-local" `
  -Labels "integrado-web-xd,deploy-local" `
  -ReplaceExisting
```

## Recuperacao se o runner antigo ficou preso no GitHub
Segundo a documentacao oficial do GitHub, se voce precisar reaproveitar a maquina e o runner antigo nao estiver mais acessivel, voce pode remover o registro antigo no GitHub ou apagar o arquivo `.runner` no diretorio do runner antes de registrar de novo.

Fonte oficial:
- [Removing self-hosted runners](https://docs.github.com/actions/how-tos/manage-runners/self-hosted-runners/remove-runners)

## O que manter salvo para retomada
- caminho do runner local: `C:\actions-runner-integrado-web-xd`
- nome do runner
- labels usadas
- nome do workflow self-hosted
- nome dos secrets usados
- chave publica instalada na VPS
- procedimento de recuperacao deste documento

## Estrategia recomendada de continuidade
Para nao ficar bloqueado depois de formatacao:
- manter este workflow self-hosted como principal para deploy local
- manter o deploy manual na VPS como fallback operacional
- nao depender de artefatos unicos fora do repositorio
- registrar o host key da VPS e o usuario de deploy na documentacao
