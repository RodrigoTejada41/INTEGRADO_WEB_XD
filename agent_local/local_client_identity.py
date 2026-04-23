from __future__ import annotations

import json
import secrets
import socket
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(slots=True)
class LocalClientIdentity:
    client_id: str
    token: str
    hostname: str


class LocalClientIdentityStore:
    def __init__(self, identity_file: str) -> None:
        self.identity_file = Path(identity_file)

    def load_or_create(self) -> LocalClientIdentity:
        if self.identity_file.exists():
            try:
                data = json.loads(self.identity_file.read_text(encoding="utf-8"))
                client_id = str(data.get("client_id", "")).strip()
                token = str(data.get("token", "")).strip()
                hostname = str(data.get("hostname", "")).strip() or socket.gethostname()
                if client_id and token:
                    return LocalClientIdentity(client_id=client_id, token=token, hostname=hostname)
            except Exception:
                pass

        identity = LocalClientIdentity(
            client_id=str(uuid4()),
            token=secrets.token_urlsafe(48),
            hostname=socket.gethostname(),
        )
        self.save(identity)
        return identity

    def save(self, identity: LocalClientIdentity) -> None:
        self.identity_file.parent.mkdir(parents=True, exist_ok=True)
        self.identity_file.write_text(
            json.dumps(
                {
                    "client_id": identity.client_id,
                    "token": identity.token,
                    "hostname": identity.hostname,
                },
                ensure_ascii=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

