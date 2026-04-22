from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_context_var: ContextVar[dict[str, object]] = ContextVar("correlation_context", default={})


def get_correlation_id() -> str | None:
    return _correlation_id_var.get()


def get_log_context() -> dict[str, object]:
    base = dict(_context_var.get())
    correlation_id = get_correlation_id()
    if correlation_id:
        base.setdefault("correlation_id", correlation_id)
    return base


@contextmanager
def bind_correlation_id(correlation_id: str | None) -> Iterator[None]:
    token: Token[str | None] = _correlation_id_var.set(correlation_id)
    try:
        yield
    finally:
        _correlation_id_var.reset(token)


@contextmanager
def bind_log_context(**values: object) -> Iterator[None]:
    current = dict(_context_var.get())
    merged = dict(current)
    for key, value in values.items():
        if value is not None:
            merged[key] = value
    token: Token[dict[str, object]] = _context_var.set(merged)
    try:
        yield
    finally:
        _context_var.reset(token)
