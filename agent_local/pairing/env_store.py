from __future__ import annotations

from pathlib import Path


class EnvStore:
    def __init__(self, env_file: Path):
        self.env_file = env_file

    def update_values(self, updates: dict[str, str]) -> None:
        self.env_file.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = []
        if self.env_file.exists():
            lines = self.env_file.read_text(encoding="utf-8").splitlines()

        keys_done: set[str] = set()
        output_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                output_lines.append(line)
                continue

            key, _ = line.split("=", 1)
            key = key.strip()
            if key in updates:
                output_lines.append(f"{key}={updates[key]}")
                keys_done.add(key)
                continue

            output_lines.append(line)

        for key, value in updates.items():
            if key not in keys_done:
                output_lines.append(f"{key}={value}")

        self.env_file.write_text("\n".join(output_lines).rstrip() + "\n", encoding="utf-8")

