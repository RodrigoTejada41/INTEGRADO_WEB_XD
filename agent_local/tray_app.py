from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path


APP_NAME = "MoviSync"
AGENT_MODULE = "agent_local.main"
PID_FILE = Path("agent_local/data/agent-sync.pid")
LOG_FILE = Path("logs/agent-sync.log")


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS


def _python_executable() -> str:
    executable = Path(sys.executable)
    if os.name == "nt":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(executable)


def _read_pid() -> int | None:
    try:
        value = PID_FILE.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=_creation_flags(),
        )
    except Exception:
        return False
    return f'"{pid}"' in result.stdout or f",{pid}," in result.stdout


def _find_agent_pids() -> list[int]:
    if os.name != "nt":
        return []
    root = str(Path.cwd()).replace("'", "''")
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','pythonw.exe') "
        f"-and $_.CommandLine -like '*{root}*' "
        "-and $_.CommandLine -like '*agent_local.main*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except Exception:
        return []
    pids: list[int] = []
    for line in result.stdout.splitlines():
        try:
            pids.append(int(line.strip()))
        except ValueError:
            continue
    return pids


def is_agent_running() -> bool:
    pid = _read_pid()
    if pid and _is_process_running(pid):
        return True
    pids = _find_agent_pids()
    if pids:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pids[0]), encoding="ascii")
        return True
    return False


def start_agent() -> str:
    if is_agent_running():
        return "Sincronizador ja esta ativo."

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log_handle = LOG_FILE.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [_python_executable(), "-m", AGENT_MODULE],
        cwd=Path.cwd(),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=_creation_flags(),
        close_fds=True,
    )
    PID_FILE.write_text(str(process.pid), encoding="ascii")
    return "Sincronizador iniciado."


def stop_agent() -> str:
    pid = _read_pid()
    pids = [pid] if pid and _is_process_running(pid) else []
    for item in _find_agent_pids():
        if item not in pids:
            pids.append(item)
    if not pids:
        try:
            PID_FILE.unlink()
        except FileNotFoundError:
            pass
        return "Sincronizador ja esta parado."

    for item in pids:
        subprocess.run(
            ["taskkill", "/PID", str(item), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_creation_flags(),
        )
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass
    return "Sincronizador parado."


def restart_agent() -> str:
    stop_agent()
    time.sleep(1)
    return start_agent()


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    subprocess.Popen(["xdg-open", str(path)])


def open_panel() -> None:
    panel = Path("Abrir_Painel_Local.vbs")
    if not panel.exists():
        panel = Path("Abrir_Painel_Local.cmd")
    if panel.exists():
        _open_path(panel)


def open_log() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("", encoding="utf-8")
    _open_path(LOG_FILE)


class TrayController:
    def __init__(self) -> None:
        self.icon = None
        self.running = False
        self.status_text = "Inicializando..."

    def build_image(self, active: bool):
        from PIL import Image, ImageDraw

        color = (36, 168, 88) if active else (210, 60, 48)
        outline = (18, 90, 48) if active else (120, 20, 20)
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((6, 6, 58, 58), fill=color, outline=outline, width=4)
        draw.rectangle((28, 16, 36, 38), fill=(255, 255, 255, 255))
        draw.polygon([(22, 36), (42, 36), (32, 50)], fill=(255, 255, 255, 255))
        return image

    def refresh(self) -> None:
        active = is_agent_running()
        self.running = active
        self.status_text = "MoviSync ativo" if active else "MoviSync parado"
        if self.icon:
            self.icon.icon = self.build_image(active)
            self.icon.title = self.status_text

    def notify(self, message: str) -> None:
        self.refresh()
        if self.icon:
            try:
                self.icon.notify(message, APP_NAME)
            except Exception:
                pass

    def on_start(self, _icon=None, _item=None) -> None:
        self.notify(start_agent())

    def on_stop(self, _icon=None, _item=None) -> None:
        self.notify(stop_agent())

    def on_restart(self, _icon=None, _item=None) -> None:
        self.notify(restart_agent())

    def on_open_panel(self, _icon=None, _item=None) -> None:
        open_panel()

    def on_open_log(self, _icon=None, _item=None) -> None:
        open_log()

    def on_exit(self, icon, _item=None) -> None:
        icon.stop()

    def monitor(self) -> None:
        while True:
            self.refresh()
            time.sleep(5)

    def run(self) -> None:
        import pystray
        from pystray import Menu, MenuItem

        self.refresh()
        menu = Menu(
            MenuItem(lambda _: self.status_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Iniciar sincronizacao", self.on_start),
            MenuItem("Parar sincronizacao", self.on_stop),
            MenuItem("Reiniciar sincronizacao", self.on_restart),
            Menu.SEPARATOR,
            MenuItem("Abrir painel local", self.on_open_panel),
            MenuItem("Abrir log", self.on_open_log),
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
        print(f"Dependencia do icone ausente: {exc}")
        print("Reinstale o pacote atualizado do MoviSync.")
        return 1
    TrayController().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
