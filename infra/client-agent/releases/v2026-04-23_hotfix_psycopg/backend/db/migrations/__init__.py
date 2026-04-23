from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
import pkgutil
from types import ModuleType
from typing import Callable

from sqlalchemy import Engine


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    upgrade: Callable[[Engine], None]
    downgrade: Callable[[Engine], None]


def _load_migration_module(package_name: str, module_name: str) -> ModuleType:
    return import_module(f"{package_name}.{module_name}")


def list_migrations() -> list[Migration]:
    migrations: list[Migration] = []
    package_dir = Path(__file__).resolve().parent
    package_name = __name__

    for module_info in pkgutil.iter_modules([str(package_dir)]):
        module_name = module_info.name
        if not module_name.startswith("v"):
            continue

        module = _load_migration_module(package_name, module_name)
        version = int(getattr(module, "VERSION"))
        name = str(getattr(module, "NAME"))
        upgrade = getattr(module, "upgrade")
        downgrade = getattr(module, "downgrade")
        migrations.append(
            Migration(
                version=version,
                name=name,
                upgrade=upgrade,
                downgrade=downgrade,
            )
        )

    return sorted(migrations, key=lambda item: item.version)

