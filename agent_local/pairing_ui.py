from __future__ import annotations

import logging
import threading
import tkinter as tk
from dataclasses import asdict
from tkinter import ttk, messagebox

from agent_local.pairing.service import ManualConfigRequest, PairingRequest, PairingService


DEFAULT_API_BASE_URL = "https://movisystecnologia.com.br/admin/api"
DEFAULT_API_KEY_FILE = "agent_local/data/agent_api_key.txt"
DEFAULT_ENV_FILE = ".env"
DEFAULT_DEVICE_LABEL = "loja-01"


class PairingWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MoviSync Vinculacao")
        self.geometry("720x520")
        self.minsize(660, 480)

        self.service = PairingService()
        self.logger = logging.getLogger("agent_local.pairing_ui")

        self.api_base_url_var = tk.StringVar(value=DEFAULT_API_BASE_URL)
        self.pairing_code_var = tk.StringVar()
        self.empresa_id_var = tk.StringVar()
        self.device_label_var = tk.StringVar(value=DEFAULT_DEVICE_LABEL)
        self.api_key_file_var = tk.StringVar(value=DEFAULT_API_KEY_FILE)
        self.env_file_var = tk.StringVar(value=DEFAULT_ENV_FILE)
        self.api_key_var = tk.StringVar()
        self.verify_ssl_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Pronto.")

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=16)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Vinculacao do agente local", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Use o codigo de vinculacao para receber a API key e gravar .env e arquivo de chave.",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        body = ttk.Frame(self, padding=16)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        pairing_frame = ttk.LabelFrame(body, text="Vinculacao por codigo", padding=12)
        pairing_frame.grid(row=0, column=0, sticky="ew")
        pairing_frame.columnconfigure(1, weight=1)

        self._add_field(pairing_frame, 0, "URL da API", self.api_base_url_var)
        self._add_field(pairing_frame, 1, "Codigo de vinculacao", self.pairing_code_var)
        self._add_field(pairing_frame, 2, "Empresa ID (opcional)", self.empresa_id_var)
        self._add_field(pairing_frame, 3, "Dispositivo", self.device_label_var)
        self._add_field(pairing_frame, 4, "Arquivo da chave", self.api_key_file_var)
        self._add_field(pairing_frame, 5, "Arquivo .env", self.env_file_var)

        ttk.Checkbutton(pairing_frame, text="Validar SSL", variable=self.verify_ssl_var).grid(
            row=6, column=1, sticky="w", pady=(6, 0)
        )

        actions = ttk.Frame(pairing_frame)
        actions.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)

        ttk.Button(actions, text="Testar API", command=self._on_test_server).grid(row=0, column=0, sticky="w")
        ttk.Button(actions, text="Vincular", command=self._on_pair).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(actions, text="Salvar configuracao manual", command=self._on_manual_save).grid(
            row=0, column=2, sticky="w", padx=(8, 0)
        )

        log_frame = ttk.LabelFrame(body, text="Status", padding=12)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.output = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.output.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Frame(self, padding=(16, 0, 16, 16))
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    def _add_field(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 12))
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=4)

    def _append_output(self, message: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", message + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def _set_busy(self, busy: bool, status: str) -> None:
        self.status_var.set(status)
        self.configure(cursor="watch" if busy else "")
        for child in self.winfo_children():
            self._toggle_child(child, not busy)

    def _toggle_child(self, widget: tk.Widget, enabled: bool) -> None:
        try:
            state = "normal" if enabled else "disabled"
            if isinstance(widget, ttk.Entry) or isinstance(widget, ttk.Button) or isinstance(widget, ttk.Checkbutton):
                widget.configure(state=state)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._toggle_child(child, enabled)

    def _run_background(self, title: str, worker: callable) -> None:
        self._set_busy(True, f"{title} em andamento...")

        def runner() -> None:
            try:
                result = worker()
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda exc=exc: self._finish_failure(title, exc))
                return
            self.after(0, lambda result=result: self._finish_success(title, result))

        threading.Thread(target=runner, daemon=True).start()

    def _finish_success(self, title: str, result: object) -> None:
        self._set_busy(False, f"{title} concluido.")
        self._append_output(f"{title}: {result}")
        messagebox.showinfo("Sucesso", f"{title} concluido.")

    def _finish_failure(self, title: str, exc: Exception) -> None:
        self._set_busy(False, f"{title} falhou.")
        self._append_output(f"{title} falhou: {exc}")
        messagebox.showerror("Erro", str(exc))

    def _on_test_server(self) -> None:
        api_base_url = self.api_base_url_var.get().strip()
        verify_ssl = self.verify_ssl_var.get()

        def worker() -> str:
            return self.service.test_server(api_base_url, verify_ssl=verify_ssl)

        self._run_background("Teste da API", worker)

    def _on_pair(self) -> None:
        pairing_code = self.pairing_code_var.get().strip()
        if not pairing_code:
            messagebox.showwarning("Validacao", "Informe o codigo de vinculacao.")
            return

        request = PairingRequest(
            api_base_url=self.api_base_url_var.get().strip(),
            pairing_code=pairing_code,
            device_label=self.device_label_var.get().strip() or DEFAULT_DEVICE_LABEL,
            empresa_id=self.empresa_id_var.get().strip(),
            api_key_file=self.api_key_file_var.get().strip() or DEFAULT_API_KEY_FILE,
            env_file=self.env_file_var.get().strip() or DEFAULT_ENV_FILE,
        )

        self._run_background("Vinculacao", lambda: asdict(self.service.activate(request)))

    def _on_manual_save(self) -> None:
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Validacao", "Informe a API key para configuracao manual.")
            return

        request = ManualConfigRequest(
            api_base_url=self.api_base_url_var.get().strip(),
            empresa_id=self.empresa_id_var.get().strip(),
            api_key=api_key,
            api_key_file=self.api_key_file_var.get().strip() or DEFAULT_API_KEY_FILE,
            device_label=self.device_label_var.get().strip() or DEFAULT_DEVICE_LABEL,
            env_file=self.env_file_var.get().strip() or DEFAULT_ENV_FILE,
            verify_ssl=self.verify_ssl_var.get(),
        )

        self._run_background("Configuracao manual", lambda: asdict(self.service.save_manual_config(request)))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = PairingWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
