import json
from datetime import UTC, datetime
from pathlib import Path


class CheckpointStore:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> datetime:
        payload = self._read()
        value = payload.get(key)
        if not value:
            return datetime(1970, 1, 1, tzinfo=UTC)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed

    def set(self, key: str, value: datetime) -> None:
        payload = self._read()
        payload[key] = value.astimezone(UTC).isoformat()
        self.file_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )

    def _read(self) -> dict:
        if not self.file_path.exists():
            return {}
        content = self.file_path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        return json.loads(content)

