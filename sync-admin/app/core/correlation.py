from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_correlation_id_var: ContextVar[str | None] = ContextVar("sync_admin_correlation_id", default=None)
_request_id_var: ContextVar[str | None] = ContextVar("sync_admin_request_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id_var.get()


def get_request_id() -> str | None:
    return _request_id_var.get()


def get_log_context() -> dict[str, object]:
    context: dict[str, object] = {}
    request_id = get_request_id()
    correlation_id = get_correlation_id()
    if request_id:
        context["request_id"] = request_id
    if correlation_id:
        context["correlation_id"] = correlation_id
    return context


@contextmanager
def bind_request_context(*, request_id: str | None, correlation_id: str | None) -> Iterator[None]:
    request_token: Token[str | None] = _request_id_var.set(request_id)
    correlation_token: Token[str | None] = _correlation_id_var.set(correlation_id)
    try:
        yield
    finally:
        _request_id_var.reset(request_token)
        _correlation_id_var.reset(correlation_token)
