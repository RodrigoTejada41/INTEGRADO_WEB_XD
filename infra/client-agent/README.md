# Cliente local - Instalador 1 clique

Este pacote instala somente o agente local no Windows, com painel local para banco, vinculacao e sincronizacao.

## Execucao rapida

1. Abra `COMECE_AQUI.bat`.
2. Clique em `Sim` quando o Windows pedir permissao.
3. Aguarde a instalacao terminar.
4. No painel que abre automaticamente:
   - informe o codigo de vinculacao;
   - configure o banco MariaDB local;
   - clique para testar e salvar.
5. Use o atalho `MoviSync Iniciar Agente` na area de trabalho.

Compatibilidade:
- `Setup_Instalar_Cliente.bat` continua existindo, mas agora chama o fluxo guiado.

## Painel local

O painel local permite configurar sem editar JSON ou `.env` manualmente:

- servidor web;
- vinculacao por codigo;
- banco local MariaDB;
- teste de conexao do banco;
- salvamento de host, porta, banco, usuario, senha, intervalo e lote.

## Arquivos criados no computador do cliente

- `C:\MoviSyncAgent`
- Atalho `MoviSync Painel Local` na area de trabalho
- Atalho `MoviSync Iniciar Agente` na area de trabalho
- Log em `C:\MoviSyncAgent\logs\agent-sync.log`

## Gerar pasta versionada do instalador

No repositorio, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\client-agent\build-release.ps1
```

Isso cria uma pasta em `infra/client-agent/releases/vYYYY-MM-DD_HHMM` com todo o pacote pronto para distribuicao.

## Resultado esperado

- Instalacao em `C:\MoviSyncAgent`
- Virtualenv local com dependencias
- `.env` criado automaticamente
- Tela Python para:
  - vinculacao por codigo
  - configuracao de banco MariaDB por formulario
  - teste de conexao do banco
  - troca manual de servidor/chave (protegida por senha)
