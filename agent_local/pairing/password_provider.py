from __future__ import annotations

import ctypes
import os
from ctypes import POINTER, Structure, WinDLL, byref, c_void_p, string_at

from ctypes import wintypes


_CRED_TYPE_GENERIC = 1
_CREDENTIAL_TARGET = "MoviSyncAgentManualConfig"


class _CREDENTIALW(Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", c_void_p),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def _read_from_windows_credential_manager(target: str) -> str | None:
    if os.name != "nt":
        return None

    advapi32 = WinDLL("advapi32", use_last_error=True)
    cred_ptr = POINTER(_CREDENTIALW)()
    cred_read = advapi32.CredReadW
    cred_read.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, POINTER(POINTER(_CREDENTIALW))]
    cred_read.restype = wintypes.BOOL

    if not cred_read(target, _CRED_TYPE_GENERIC, 0, byref(cred_ptr)):
        return None

    try:
        blob_size = int(cred_ptr.contents.CredentialBlobSize)
        blob_ptr = cred_ptr.contents.CredentialBlob
        if not blob_ptr or blob_size <= 0:
            return None

        data = string_at(blob_ptr, blob_size)
        try:
            return data.decode("utf-16-le").rstrip("\x00")
        except UnicodeDecodeError:
            return data.decode("utf-8", errors="ignore").rstrip("\x00")
    finally:
        cred_free = advapi32.CredFree
        cred_free.argtypes = [c_void_p]
        cred_free.restype = None
        cred_free(cred_ptr)


def resolve_manual_config_password() -> str:
    password = _read_from_windows_credential_manager(_CREDENTIAL_TARGET)
    if password:
        return password

    env_value = os.getenv("AGENT_MANUAL_CONFIG_PASSWORD", "").strip()
    if env_value:
        return env_value

    return "25032015"


def resolve_manual_config_target() -> str:
    return _CREDENTIAL_TARGET

