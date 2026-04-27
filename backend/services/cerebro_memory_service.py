from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.repositories.cerebro_memory_repository import CerebroMemoryRepository

settings = get_settings()

DEFAULT_MEMORY = {
    "project_context": {
        "name": "",
        "objectives": [],
        "architecture": [],
    },
    "technical_decisions": [],
    "completed_tasks": [],
    "user_preferences": [],
    "known_issues": [],
}


def _unique_merge(items: list[Any], incoming: list[Any]) -> list[Any]:
    merged = list(items)
    for value in incoming:
        if value not in merged:
            merged.append(value)
    return merged


def _normalize(memory: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "project_context": {
            "name": "",
            "objectives": [],
            "architecture": [],
        },
        "technical_decisions": [],
        "completed_tasks": [],
        "user_preferences": [],
        "known_issues": [],
    }
    project_context = memory.get("project_context", {})
    normalized["project_context"]["name"] = str(project_context.get("name", "") or "")
    normalized["project_context"]["objectives"] = [
        str(value) for value in project_context.get("objectives", []) if str(value).strip()
    ]
    normalized["project_context"]["architecture"] = [
        str(value) for value in project_context.get("architecture", []) if str(value).strip()
    ]
    for key in (
        "technical_decisions",
        "completed_tasks",
        "user_preferences",
        "known_issues",
    ):
        normalized[key] = [str(value) for value in memory.get(key, []) if str(value).strip()]
    return normalized


class CerebroMemoryService:
    def __init__(
        self,
        repository: CerebroMemoryRepository,
        json_backup_path: str | None = None,
    ) -> None:
        self._repository = repository
        self._json_backup_path = Path(json_backup_path or settings.memory_json_backup_path)

    def get_memory(self, project_tag: str) -> tuple[dict[str, Any], str]:
        db_record = self._safe_get_from_db(project_tag)
        if db_record is not None:
            return db_record, "DB"

        json_record = self._read_json_backup(project_tag)
        if json_record is not None:
            return json_record, "JSON"

        memory = dict(DEFAULT_MEMORY)
        memory["project_context"] = dict(memory["project_context"])
        memory["project_context"]["name"] = project_tag
        return memory, "EMPTY"

    def store_memory(self, project_tag: str, incoming_memory: dict[str, Any]) -> tuple[dict[str, Any], str]:
        current_memory, source = self.get_memory(project_tag)
        merged = self._merge_memory(current_memory, _normalize(incoming_memory))
        payload_json = json.dumps(merged, ensure_ascii=False)

        db_status = self._safe_upsert_db(project_tag, payload_json)
        json_status = self._write_json_backup(project_tag, merged)

        stored_source = "DB+JSON" if db_status and json_status else "JSON" if json_status else "DB"
        if not db_status and not json_status:
            stored_source = source
        return merged, stored_source

    def _safe_get_from_db(self, project_tag: str) -> dict[str, Any] | None:
        try:
            record = self._repository.get_by_project_tag(project_tag)
            if record is None:
                return None
            return _normalize(json.loads(record.payload_json))
        except Exception:
            return None

    def _safe_upsert_db(self, project_tag: str, payload_json: str) -> bool:
        try:
            self._repository.upsert(project_tag=project_tag, payload_json=payload_json)
            self._repository.session.commit()
            return True
        except Exception:
            self._repository.session.rollback()
            return False

    def _read_json_backup(self, project_tag: str) -> dict[str, Any] | None:
        path = self._json_backup_path
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            project = raw.get("projects", {}).get(project_tag, {})
            memory = project.get("memory")
            if isinstance(memory, dict):
                return _normalize(memory)
            return None
        except Exception:
            return None

    def _write_json_backup(self, project_tag: str, memory: dict[str, Any]) -> bool:
        path = self._json_backup_path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload: dict[str, Any] = {}
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
            projects = payload.get("projects", {})
            projects[project_tag] = {
                "memory": memory,
            }
            payload["projects"] = projects
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    @staticmethod
    def _merge_memory(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = _normalize(current)
        merged_incoming = _normalize(incoming)

        if merged_incoming["project_context"]["name"]:
            merged["project_context"]["name"] = merged_incoming["project_context"]["name"]
        merged["project_context"]["objectives"] = _unique_merge(
            merged["project_context"]["objectives"],
            merged_incoming["project_context"]["objectives"],
        )
        merged["project_context"]["architecture"] = _unique_merge(
            merged["project_context"]["architecture"],
            merged_incoming["project_context"]["architecture"],
        )
        for key in (
            "technical_decisions",
            "completed_tasks",
            "user_preferences",
            "known_issues",
        ):
            merged[key] = _unique_merge(merged[key], merged_incoming[key])
        return merged
