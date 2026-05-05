from __future__ import annotations

import os
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from agent_local.windows_autostart import (
    DEFAULT_LOCAL_API_PORT,
    find_process_ids,
    start_local_api,
)


APP_NAME = "Movi_commanda API"
LOG_FILE = Path("logs/local-api.log")
DEFAULT_TOKEN_FILE = Path("agent_local/data/local_api_token.txt")


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS


def _local_api_port() -> str:
    return os.getenv("LOCAL_API_PORT", DEFAULT_LOCAL_API_PORT).strip() or DEFAULT_LOCAL_API_PORT


def _base_url() -> str:
    return f"http://127.0.0.1:{_local_api_port()}"


def _read_local_token() -> str | None:
    token_file = Path(os.getenv("LOCAL_API_TOKEN_FILE", str(DEFAULT_TOKEN_FILE)) or DEFAULT_TOKEN_FILE)
    try:
        token = token_file.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    return token or None


def _fetch_status() -> dict[str, object] | None:
    token = _read_local_token()
    if not token:
        return None
    request = urllib.request.Request(
        f"{_base_url()}/orders/technical/status",
        headers={"X-Local-Token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def is_api_running() -> bool:
    try:
        with urllib.request.urlopen(f"{_base_url()}/health", timeout=2) as response:
            return response.status == 200 and b'"ok"' in response.read(200)
    except (OSError, urllib.error.URLError):
        return False


def stop_local_api() -> str:
    pids = find_process_ids("agent_local.local_api")
    if not pids:
        return "API local ja esta parada."
    for pid in pids:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_creation_flags(),
        )
    return "API local parada."


def restart_local_api() -> str:
    stop_local_api()
    time.sleep(1)
    started = start_local_api()
    return "API local reiniciada." if started else "API local ja estava ativa."


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", str(path)])


def open_orders() -> None:
    script = Path("Abrir_Comandas_Locais.vbs")
    if not script.exists():
        script = Path("Abrir_Comandas_Locais.cmd")
    if script.exists():
        _open_path(script)


def open_settings() -> None:
    script = Path("Abrir_Painel_Local.vbs")
    if not script.exists():
        script = Path("Abrir_Painel_Local.cmd")
    if script.exists():
        _open_path(script)


def open_log() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("", encoding="utf-8")
    _open_path(LOG_FILE)


class ApiTrayController:
    def __init__(self) -> None:
        self.icon = None
        self.running = False
        self.status_text = "Inicializando API local..."
        self.server_url = "IP servidor indisponivel"
        self.web_clients_text = "Clientes web: indisponivel"

    def build_image(self, active: bool):
        from PIL import Image, ImageDraw

        color = (36, 168, 88) if active else (210, 60, 48)
        outline = (18, 90, 48) if active else (120, 20, 20)
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=color, outline=outline, width=4)
        draw.text((18, 22), "API", fill=(255, 255, 255, 255))
        return image

    def refresh(self) -> None:
        active = is_api_running()
        self.running = active
        self.status_text = "Movi_commanda API ativa" if active else "Movi_commanda API parada"
        status = _fetch_status() if active else None
        network = status.get("network") if isinstance(status, dict) else None
        if isinstance(network, dict) and network.get("access_url"):
            self.server_url = f"IP servidor: {network['access_url']}"
        else:
            self.server_url = "IP servidor indisponivel"
        if isinstance(status, dict):
            self.web_clients_text = f"Clientes web conectados: {int(status.get('web_clients_count') or 0)}"
        else:
            self.web_clients_text = "Clientes web: indisponivel"
        if self.icon:
            self.icon.icon = self.build_image(active)
            self.icon.title = f"{self.status_text} | {self.web_clients_text}"

    def notify(self, message: str) -> None:
        self.refresh()
        if self.icon:
            try:
                self.icon.notify(message, APP_NAME)
            except Exception:
                pass

    def on_start(self, _icon=None, _item=None) -> None:
        started = start_local_api()
        self.notify("API local iniciada." if started else "API local ja esta ativa.")

    def on_restart(self, _icon=None, _item=None) -> None:
        self.notify(restart_local_api())

    def on_open_orders(self, _icon=None, _item=None) -> None:
        if not is_api_running():
            start_local_api()
            time.sleep(1)
        open_orders()

    def on_open_settings(self, _icon=None, _item=None) -> None:
        open_settings()

    def on_open_log(self, _icon=None, _item=None) -> None:
        open_log()

    def on_show_web_status(self, _icon=None, _item=None) -> None:
        self.refresh()
        self.notify(f"{self.server_url}\n{self.web_clients_text}")

    def on_exit(self, icon, _item=None) -> None:
        icon.stop()

    def monitor(self) -> None:
        while True:
            self.refresh()
            time.sleep(30)

    def run(self) -> None:
        import pystray
        from pystray import Menu, MenuItem

        self.refresh()
        menu = Menu(
            MenuItem(lambda _: self.status_text, None, enabled=False),
            MenuItem(lambda _: self.server_url, None, enabled=False),
            MenuItem(lambda _: self.web_clients_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Abrir comandas", self.on_open_orders),
            MenuItem("Abrir configuracoes", self.on_open_settings),
            MenuItem("Ver clientes conectados", self.on_show_web_status),
            Menu.SEPARATOR,
            MenuItem("Iniciar API local", self.on_start),
            MenuItem("Reiniciar API local", self.on_restart),
            MenuItem("Abrir log da API", self.on_open_log),
            Menu.SEPARATOR,
            MenuItem("Fechar icone", self.on_exit),
        )
        self.icon = pystray.Icon(APP_NAME, self.build_image(self.running), self.status_text, menu)
        threading.Thread(target=self.monitor, daemon=True).start()
        self.icon.run()


def main() -> int:
    os.chdir(Path(__file__).resolve().parents[1])
    try:
        import pystray  # noqa: F401
        import PIL  # noqa: F401
    except Exception as exc:
        print(f"Dependencias do icone ausentes: {exc}")
        return 1
    ApiTrayController().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
