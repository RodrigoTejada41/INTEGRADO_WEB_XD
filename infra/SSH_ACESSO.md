# Acesso SSH e Chaves (Operacional)

Este arquivo registra **onde as chaves ficam** e **como usar** no deploy, sem armazenar segredo no repositorio.

## Chave atualmente usada para deploy/acesso
- Host VPS: `172.238.213.72`
- Usuario: `root`
- Chave local utilizada: `C:\Users\Rodrigo Tejada\.ssh\movisys_vps`
- Publica correspondente: `C:\Users\Rodrigo Tejada\.ssh\movisys_vps.pub`

## Comandos rapidos (PowerShell)

Conectar na VPS:
```powershell
ssh -i "$HOME\.ssh\movisys_vps" root@172.238.213.72
```

Executar update/deploy remoto:
```powershell
ssh -i "$HOME\.ssh\movisys_vps" root@172.238.213.72 "cd /opt/integrado_web_xd && bash infra/scripts/update.sh"
```

Atalho do projeto:
```powershell
.\infra\scripts\ssh-prod.ps1
.\infra\scripts\ssh-prod.ps1 -RemoteCommand "cd /opt/integrado_web_xd && bash infra/scripts/update.sh"
```

Validar health remoto:
```powershell
ssh -i "$HOME\.ssh\movisys_vps" root@172.238.213.72 "curl -f http://127.0.0.1/healthz && curl -f http://127.0.0.1/api/health/ready"
```

## GitHub Actions (secrets)
Secrets configurados para deploy automatico:
- `VPS_HOST=172.238.213.72`
- `VPS_USER=root`
- `VPS_PORT=22`
- `VPS_APP_DIR=/opt/integrado_web_xd`
- `VPS_SSH_KEY` = conteudo da chave privada local `movisys_vps` (armazenado no GitHub Secret)

## Regra de seguranca
- Nao salvar chave privada dentro deste repositorio.
- Manter chave privada apenas em:
  - pasta local segura (`~/.ssh`), e/ou
  - cofre de segredos corporativo, e/ou
  - GitHub Secrets (para CI/CD).

## Proximo endurecimento recomendado
1. Criar usuario dedicado `deploy` na VPS.
2. Trocar `VPS_USER=root` para `deploy`.
3. Rotacionar chave para uma chave exclusiva deste projeto.
4. Desabilitar login root por senha.
