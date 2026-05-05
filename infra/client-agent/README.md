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
5. Use os atalhos criados para a API instalada.

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

- API Comanda:
  - `C:\Movi_commanda`
  - Atalho `Movi_commanda Definicoes` na area de trabalho
  - Atalho `Movi_commanda` na area de trabalho
  - Arquivo de acesso em rede: `C:\Movi_commanda\ACESSO_REDE_LOCAL.txt`
- API Sync Relatorios:
  - `C:\MoviSyncAgent`
  - Atalho `MoviSync Relatorios Configurar` na area de trabalho
  - Atalho `MoviSync Relatorios Status` na area de trabalho
  - Atalho `MoviSync Relatorios Iniciar` na area de trabalho
  - Log em `C:\MoviSyncAgent\logs\agent-sync.log`

## Separacao operacional

As duas APIs ficam em pastas separadas.

- Comandas:
  - pasta `C:\Movi_commanda`
  - `Iniciar_Movi_commanda_Windows.vbs`
  - `Abrir_Comandas_Locais.vbs`
  - rotas `/orders/*`
  - cache `agent_local\data\local_orders.db`
- Relatorios/sync:
  - pasta `C:\MoviSyncAgent`
  - `Iniciar_Relatorios_Sync.cmd`
  - `Abrir_Status_Relatorios.cmd`
  - processo `agent_local.main`
  - logs `logs\agent-sync.log`

O instalador da Comanda nao remove nem sobrescreve `C:\MoviSyncAgent`.
O instalador do Sync Relatorios nao remove nem sobrescreve `C:\Movi_commanda`.

## Acesso em rede local

O computador onde o instalador roda vira o servidor local das comandas.

- A API escuta na porta `8765`.
- Celulares e tablets devem estar no mesmo Wi-Fi/rede local.
- O endereco para os dispositivos fica em `C:\Movi_commanda\ACESSO_REDE_LOCAL.txt`.
- O cache operacional fica em `C:\Movi_commanda\agent_local\data\local_orders.db`.
- O SQLite local usa WAL e timeout para suportar multiplos dispositivos gravando na mesma base local.
- O instalador cria a regra de firewall `Movi_commanda API Local` para liberar entrada TCP na rede privada.

## Icone perto do relogio

O icone `Movi_commanda` fica na bandeja do Windows:

- verde: sincronizador ativo;
- vermelho: sincronizador parado.

Clique com o botao direito para:

- iniciar sincronizacao;
- parar sincronizacao;
- reiniciar sincronizacao;
- abrir painel local;
- abrir log.

## Gerar pasta versionada do instalador

No repositorio, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\client-agent\build-release.ps1
```

Isso cria uma pasta em `infra/client-agent/releases/vYYYY-MM-DD_HHMM` com todo o pacote pronto para distribuicao.

## Resultado esperado

- Instalacao em `C:\Movi_commanda`
- Virtualenv local com dependencias
- `.env` criado automaticamente
- Icone de status perto do relogio do Windows
- Tela Python para:
  - vinculacao por codigo
  - configuracao de banco MariaDB por formulario
  - teste de conexao do banco
  - troca manual de servidor/chave (protegida por senha)
