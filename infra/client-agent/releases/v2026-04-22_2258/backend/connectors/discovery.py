from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import TypeVar

TConnector = TypeVar("TConnector")


def _load_package_modules(package_name: str) -> None:
    package = importlib.import_module(package_name)
    package_paths = getattr(package, "__path__", None)
    if package_paths is None:
        return

    for module_info in pkgutil.walk_packages(package_paths, package.__name__ + "."):
        importlib.import_module(module_info.name)


def discover_connector_classes(package_name: str, base_class: type[TConnector]) -> list[type[TConnector]]:
    _load_package_modules(package_name)
    package = importlib.import_module(package_name)
    package_paths = getattr(package, "__path__", None)
    if package_paths is None:
        return []

    discovered: list[type[TConnector]] = []
    for module_info in pkgutil.walk_packages(package_paths, package.__name__ + "."):
        module = importlib.import_module(module_info.name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if candidate is base_class:
                continue
            if not issubclass(candidate, base_class):
                continue
            if not candidate.__module__.startswith(package_name):
                continue
            discovered.append(candidate)

    unique_classes: list[type[TConnector]] = []
    seen: set[type[TConnector]] = set()
    for candidate in discovered:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_classes.append(candidate)

    return sorted(unique_classes, key=lambda item: getattr(item, "connector_type", item.__name__))
