from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from agent_local.pairing.password_provider import (
    resolve_manual_config_password,
    resolve_manual_config_target,
)
from agent_local.pairing.service import ManualConfigRequest, PairingRequest, PairingService


class PairingWindow:
    def __init__(self) -> None:
        self.service = PairingService()
        self.manual_config_password = resolve_manual_config_password()
        self.manual_config_target = resolve_manual_config_target()
        self.root = tk.Tk()
        self.root.title("MoviSync - Configuracao da API Local")
        self.root.geometry("760x470")
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
        self.status_var = tk.StringVar(
            value=f"Pronto. Senha manual protegida por Windows Credential Manager target={self.manual_config_target}."
        )

        self._build_form()

    def _build_form(self) -> None:
        wrapper = ttk.Frame(self.root, padding=14)
        wrapper.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(wrapper)
        notebook.pack(fill=tk.BOTH, expand=True)

        pairing_tab = ttk.Frame(notebook, padding=12)
        manual_tab = ttk.Frame(notebook, padding=12)
        notebook.add(pairing_tab, text="Vinculacao por Codigo")
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

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    PairingWindow().run()


if __name__ == "__main__":
    main()
