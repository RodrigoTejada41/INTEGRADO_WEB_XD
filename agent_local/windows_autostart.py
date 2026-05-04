from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT_DIR / "logs"
LOCK_FILE = ROOT_DIR / "agent_local" / "data" / "windows-autostart.lock"
DEFAULT_LOCAL_API_HOST = "0.0.0.0"
DEFAULT_LOCAL_API_PORT = "8765"
LOCK_TTL_SECONDS = 60


def _creation_flags() -> int:
    if os.name != "nt":
        return 0
    return subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS


def _pythonw_executable() -> str:
    executable = Path(sys.executable)
    if os.name == "nt":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(executable)


def find_process_ids(command_fragment: str) -> list[int]:
    if os.name != "nt":
        return []
    root = str(ROOT_DIR).replace("'", "''")
    fragment = command_fragment.replace("'", "''")
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('python.exe','pythonw.exe') "
        f"-and $_.CommandLine -like '*{root}*' "
        f"-and $_.CommandLine -like '*{fragment}*' }} | "
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

    process_ids: list[int] = []
    for line in result.stdout.splitlines():
        try:
            process_ids.append(int(line.strip()))
        except ValueError:
            continue
    return process_ids


def _start_once(command_fragment: str, args: list[str], log_name: str) -> bool:
    if find_process_ids(command_fragment):
        return False

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = (LOG_DIR / log_name).open("a", encoding="utf-8")
    subprocess.Popen(
        [_pythonw_executable(), *args],
        cwd=ROOT_DIR,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=_creation_flags(),
        close_fds=True,
    )
    return True


def start_local_api() -> bool:
    host = os.getenv("LOCAL_API_HOST", DEFAULT_LOCAL_API_HOST).strip() or DEFAULT_LOCAL_API_HOST
    port = os.getenv("LOCAL_API_PORT", DEFAULT_LOCAL_API_PORT).strip() or DEFAULT_LOCAL_API_PORT
    return _start_once(
        "agent_local.local_api",
        ["-m", "uvicorn", "agent_local.local_api:app", "--host", host, "--port", port],
        "local-api.log",
    )


def start_tray() -> bool:
    return _start_once("agent_local.tray_app", ["-m", "agent_local.tray_app"], "agent-tray.log")


def start_sync() -> bool:
    return _start_once("agent_local.main", ["-m", "agent_local.main"], "agent-sync.log")


def _acquire_startup_lock() -> bool:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        age = time.time() - LOCK_FILE.stat().st_mtime
        if age < LOCK_TTL_SECONDS:
            return False
        LOCK_FILE.unlink(missing_ok=True)
    try:
        LOCK_FILE.write_text(str(os.getpid()), encoding="ascii")
        return True
    except OSError:
        return False


def _release_startup_lock() -> None:
    try:
        if LOCK_FILE.exists() and LOCK_FILE.read_text(encoding="ascii").strip() == str(os.getpid()):
            LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        return


def main() -> int:
    os.chdir(ROOT_DIR)
    if not _acquire_startup_lock():
        return 0
    try:
        start_local_api()
        start_tray()
        start_sync()
    finally:
        _release_startup_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
