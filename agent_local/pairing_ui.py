from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

from agent_local.config.database_config import (
    DEFAULT_DATABASE_TYPE,
    DEFAULT_MARIADB_PORT,
    LocalDatabaseConfig,
    LocalDatabaseConfigService,
    parse_mariadb_url,
)
from agent_local.pairing.password_provider import (
    resolve_manual_config_password,
    resolve_manual_config_target,
)
from agent_local.pairing.service import ManualConfigRequest, PairingRequest, PairingService


class PairingWindow:
    def __init__(self) -> None:
        self.service = PairingService()
        self.database_service = LocalDatabaseConfigService()
        self.manual_config_password = resolve_manual_config_password()
        self.manual_config_target = resolve_manual_config_target()
        self.root = tk.Tk()
        self.root.title("MoviSync - Painel Local")
        self.root.geometry("820x620")
        self.root.resizable(False, False)

        self.api_base_url_var = tk.StringVar(value="https://movisystecnologia.com.br/admin/api")
        self.empresa_id_var = tk.StringVar(value="")
        self.device_label_var = tk.StringVar(value="loja-01")
        self.api_key_file_var = tk.StringVar(value="agent_local/data/agent_api_key.txt")
        self.env_file_var = tk.StringVar(value=".env")
        self.verify_ssl_var = tk.BooleanVar(value=True)

        self.pairing_code_var = tk.StringVar(value="")
        self.manual_api_key_var = tk.StringVar(value="")
        self.manual_password_var = tk.StringVar(value="")
        self.database_type_var = tk.StringVar(value=DEFAULT_DATABASE_TYPE)
        self.db_host_var = tk.StringVar(value="127.0.0.1")
        self.db_port_var = tk.StringVar(value=str(DEFAULT_MARIADB_PORT))
        self.db_name_var = tk.StringVar(value="xd")
        self.db_username_var = tk.StringVar(value="root")
        self.db_password_var = tk.StringVar(value="")
        self.db_ssl_var = tk.BooleanVar(value=False)
        self.sync_interval_var = tk.StringVar(value="15")
        self.batch_size_var = tk.StringVar(value="500")
        self.status_var = tk.StringVar(
            value=f"Pronto. Senha manual protegida por Windows Credential Manager target={self.manual_config_target}."
        )

        self._load_existing_env_defaults()
        self._build_form()

    def _load_existing_env_defaults(self) -> None:
        env_file = Path(self.env_file_var.get())
        if not env_file.exists():
            return
        values: dict[str, str] = {}
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

        self.api_base_url_var.set(values.get("AGENT_API_BASE_URL", self.api_base_url_var.get()))
        self.empresa_id_var.set(values.get("AGENT_EMPRESA_ID", self.empresa_id_var.get()))
        self.device_label_var.set(values.get("AGENT_DEVICE_LABEL", self.device_label_var.get()))
        self.api_key_file_var.set(values.get("AGENT_API_KEY_FILE", self.api_key_file_var.get()))
        self.sync_interval_var.set(values.get("SYNC_INTERVAL_MINUTES", self.sync_interval_var.get()))
        self.batch_size_var.set(values.get("BATCH_SIZE", self.batch_size_var.get()))
        self.verify_ssl_var.set(values.get("VERIFY_SSL", "true").lower() != "false")

        mariadb_url = values.get("AGENT_MARIADB_URL", "")
        if not mariadb_url:
            return
        try:
            config = parse_mariadb_url(mariadb_url)
        except Exception:
            return
        self.database_type_var.set(config.database_type)
        self.db_host_var.set(config.host)
        self.db_port_var.set(str(config.port))
        self.db_name_var.set(config.database)
        self.db_username_var.set(config.username)
        self.db_password_var.set(config.password)
        self.db_ssl_var.set(config.ssl_enabled)

    def _build_form(self) -> None:
        wrapper = ttk.Frame(self.root, padding=14)
        wrapper.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(wrapper)
        notebook.pack(fill=tk.BOTH, expand=True)

        pairing_tab = ttk.Frame(notebook, padding=12)
        database_tab = ttk.Frame(notebook, padding=12)
        manual_tab = ttk.Frame(notebook, padding=12)
        notebook.add(pairing_tab, text="Vinculacao por Codigo")
        notebook.add(database_tab, text="Banco Local")
        notebook.add(manual_tab, text="Configuracao Manual")

        self._build_common_block(pairing_tab, start_row=0)
        ttk.Label(pairing_tab, text="Codigo de vinculacao").grid(row=6, column=0, sticky=tk.W, pady=5)
        ttk.Entry(pairing_tab, textvariable=self.pairing_code_var, width=30).grid(
            row=6, column=1, sticky=tk.W, pady=5
        )
        actions_pair = ttk.Frame(pairing_tab)
        actions_pair.grid(row=7, column=1, sticky=tk.W, pady=10)
        ttk.Button(actions_pair, text="Testar Servidor", command=self._on_test_server).pack(side=tk.LEFT)
        ttk.Button(actions_pair, text="Vincular por Codigo", command=self._on_pair).pack(side=tk.LEFT, padx=8)

        self._build_database_tab(database_tab)

        self._build_common_block(manual_tab, start_row=0)
        ttk.Label(manual_tab, text="API key manual").grid(row=6, column=0, sticky=tk.W, pady=5)
        ttk.Entry(manual_tab, textvariable=self.manual_api_key_var, width=52, show="*").grid(
            row=6, column=1, sticky=tk.W, pady=5
        )
        ttk.Label(manual_tab, text="Senha de protecao").grid(row=7, column=0, sticky=tk.W, pady=5)
        ttk.Entry(manual_tab, textvariable=self.manual_password_var, width=28, show="*").grid(
            row=7, column=1, sticky=tk.W, pady=5
        )
        ttk.Label(
            manual_tab,
            text=f"Fonte da senha: Credential Manager ({self.manual_config_target})",
        ).grid(row=8, column=1, sticky=tk.W, pady=2)
        actions_manual = ttk.Frame(manual_tab)
        actions_manual.grid(row=9, column=1, sticky=tk.W, pady=10)
        ttk.Button(actions_manual, text="Testar Servidor", command=self._on_test_server).pack(side=tk.LEFT)
        ttk.Button(actions_manual, text="Salvar Configuracao", command=self._on_save_manual).pack(
            side=tk.LEFT, padx=8
        )

        footer = ttk.Frame(wrapper)
        footer.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(footer, textvariable=self.status_var, wraplength=610).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(footer, text="Fechar", command=self.root.destroy).pack(side=tk.RIGHT)

    def _build_database_tab(self, parent: ttk.Frame) -> None:
        help_text = (
            "Configure o banco do cliente. A senha fica somente nesta maquina, "
            "salva no .env local do agente."
        )
        ttk.Label(parent, text=help_text, wraplength=680).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
        )

        ttk.Label(parent, text="Tipo do banco").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(
            parent,
            textvariable=self.database_type_var,
            values=[DEFAULT_DATABASE_TYPE],
            state="readonly",
            width=27,
        ).grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Host/IP").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.db_host_var, width=42).grid(row=2, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Porta").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.db_port_var, width=12).grid(row=3, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Nome do banco").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.db_name_var, width=42).grid(row=4, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Usuario").grid(row=5, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.db_username_var, width=42).grid(row=5, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Senha").grid(row=6, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.db_password_var, width=42, show="*").grid(
            row=6, column=1, sticky=tk.W, pady=5
        )

        ttk.Checkbutton(parent, text="Usar SSL no banco", variable=self.db_ssl_var).grid(
            row=7, column=1, sticky=tk.W, pady=5
        )

        ttk.Label(parent, text="Intervalo de sincronizacao (min)").grid(row=8, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.sync_interval_var, width=12).grid(row=8, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Tamanho do lote").grid(row=9, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.batch_size_var, width=12).grid(row=9, column=1, sticky=tk.W, pady=5)

        ttk.Label(parent, text="Arquivo .env").grid(row=10, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.env_file_var, width=52).grid(row=10, column=1, sticky=tk.W, pady=5)

        actions = ttk.Frame(parent)
        actions.grid(row=11, column=1, sticky=tk.W, pady=14)
        ttk.Button(actions, text="Testar banco", command=self._on_test_database).pack(side=tk.LEFT)
        ttk.Button(actions, text="Salvar banco", command=self._on_save_database).pack(side=tk.LEFT, padx=8)

    def _build_common_block(self, parent: ttk.Frame, start_row: int) -> None:
        ttk.Label(parent, text="URL da API").grid(row=start_row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.api_base_url_var, width=52).grid(
            row=start_row, column=1, sticky=tk.W, pady=5
        )

        ttk.Label(parent, text="Empresa ID").grid(row=start_row + 1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.empresa_id_var, width=52).grid(
            row=start_row + 1, column=1, sticky=tk.W, pady=5
        )

        ttk.Label(parent, text="Dispositivo").grid(row=start_row + 2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.device_label_var, width=30).grid(
            row=start_row + 2, column=1, sticky=tk.W, pady=5
        )

        ttk.Label(parent, text="Arquivo da chave").grid(row=start_row + 3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.api_key_file_var, width=52).grid(
            row=start_row + 3, column=1, sticky=tk.W, pady=5
        )

        ttk.Label(parent, text="Arquivo .env").grid(row=start_row + 4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=self.env_file_var, width=52).grid(
            row=start_row + 4, column=1, sticky=tk.W, pady=5
        )

        ttk.Checkbutton(parent, text="Validar SSL (HTTPS)", variable=self.verify_ssl_var).grid(
            row=start_row + 5, column=1, sticky=tk.W, pady=5
        )

    def _on_test_server(self) -> None:
        try:
            status = self.service.test_server(
                api_base_url=self.api_base_url_var.get().strip(),
                verify_ssl=self.verify_ssl_var.get(),
            )
        except Exception as exc:
            self.status_var.set(f"Falha no teste do servidor: {exc}")
            messagebox.showerror("Teste de Servidor", str(exc))
            return
        self.status_var.set(f"Servidor online. health.status={status}")
        messagebox.showinfo("Teste de Servidor", "Conexao com servidor validada.")

    def _on_pair(self) -> None:
        code = self.pairing_code_var.get().strip()
        if not code:
            messagebox.showerror("Validacao", "Informe o codigo de vinculacao.")
            return
        request = PairingRequest(
            api_base_url=self.api_base_url_var.get().strip(),
            pairing_code=code,
            device_label=self.device_label_var.get().strip() or "local-agent",
            empresa_id=self.empresa_id_var.get().strip(),
            api_key_file=self.api_key_file_var.get().strip(),
            env_file=self.env_file_var.get().strip(),
        )
        try:
            result = self.service.activate(request)
        except Exception as exc:
            self.status_var.set(f"Falha na vinculacao: {exc}")
            messagebox.showerror("Erro na vinculacao", str(exc))
            return
        self.pairing_code_var.set("")
        self.empresa_id_var.set(result.empresa_id)
        self.status_var.set(
            f"Vinculacao concluida. empresa_id={result.empresa_id}. "
            f"Chave salva em {result.api_key_file} e .env atualizado."
        )
        messagebox.showinfo("Sucesso", "Vinculacao concluida.")

    def _on_save_manual(self) -> None:
        if self.manual_password_var.get().strip() != self.manual_config_password:
            self.status_var.set("Senha invalida para alterar configuracao manual do servidor.")
            messagebox.showerror("Configuracao Manual", "Senha de protecao invalida.")
            return

        request = ManualConfigRequest(
            api_base_url=self.api_base_url_var.get().strip(),
            empresa_id=self.empresa_id_var.get().strip(),
            api_key=self.manual_api_key_var.get().strip(),
            api_key_file=self.api_key_file_var.get().strip(),
            device_label=self.device_label_var.get().strip() or "local-agent",
            env_file=self.env_file_var.get().strip(),
            verify_ssl=self.verify_ssl_var.get(),
        )
        try:
            result = self.service.save_manual_config(request)
        except Exception as exc:
            self.status_var.set(f"Falha ao salvar configuracao manual: {exc}")
            messagebox.showerror("Configuracao Manual", str(exc))
            return
        self.manual_api_key_var.set("")
        self.manual_password_var.set("")
        self.status_var.set(
            f"Configuracao manual salva. empresa_id={result.empresa_id}. "
            f"Chave em {result.api_key_file}, .env atualizado."
        )
        messagebox.showinfo("Configuracao Manual", "Configuracao salva com sucesso.")

    def _build_database_config(self) -> LocalDatabaseConfig:
        try:
            port = int(self.db_port_var.get().strip())
            sync_interval = int(self.sync_interval_var.get().strip())
            batch_size = int(self.batch_size_var.get().strip())
        except ValueError as exc:
            raise RuntimeError("Porta, intervalo e tamanho do lote devem ser numeros.") from exc
        if sync_interval < 1 or sync_interval > 1440:
            raise RuntimeError("Intervalo deve ficar entre 1 e 1440 minutos.")
        if batch_size < 1 or batch_size > 5000:
            raise RuntimeError("Tamanho do lote deve ficar entre 1 e 5000.")
        return LocalDatabaseConfig(
            database_type=self.database_type_var.get().strip(),
            host=self.db_host_var.get().strip(),
            port=port,
            database=self.db_name_var.get().strip(),
            username=self.db_username_var.get().strip(),
            password=self.db_password_var.get(),
            ssl_enabled=self.db_ssl_var.get(),
            sync_interval_minutes=sync_interval,
            batch_size=batch_size,
        )

    def _on_test_database(self) -> None:
        try:
            config = self._build_database_config()
            self.database_service.test_connection(config)
        except Exception as exc:
            self.status_var.set(f"Falha ao testar banco: {exc}")
            messagebox.showerror("Teste do Banco Local", str(exc))
            return
        self.status_var.set("Banco local conectado com sucesso.")
        messagebox.showinfo("Teste do Banco Local", "Conexao com MariaDB validada.")

    def _on_save_database(self) -> None:
        try:
            config = self._build_database_config()
            result = self.database_service.save_config(
                config=config,
                env_file=self.env_file_var.get().strip(),
            )
        except Exception as exc:
            self.status_var.set(f"Falha ao salvar banco: {exc}")
            messagebox.showerror("Banco Local", str(exc))
            return
        self.status_var.set(
            f"Banco salvo. tipo={result.database_type}, host={result.host}, "
            f"database={result.database}, env={result.env_file}."
        )
        messagebox.showinfo("Banco Local", "Configuracao do banco local salva.")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    PairingWindow().run()


if __name__ == "__main__":
    main()
