from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from app.config.settings import settings
from app.core.correlation import get_log_context


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        base_fields = {
            'name',
            'msg',
            'args',
            'levelname',
            'levelno',
            'pathname',
            'filename',
            'module',
            'exc_info',
            'exc_text',
            'stack_info',
            'lineno',
            'funcName',
            'created',
            'msecs',
            'relativeCreated',
            'thread',
            'threadName',
            'processName',
            'process',
        }
        extra_context = {
            key: value
            for key, value in record.__dict__.items()
            if key not in base_fields and not key.startswith('_')
        }
        correlation_context = get_log_context()
        if correlation_context:
            for key, value in correlation_context.items():
                extra_context.setdefault(key, value)
        if extra_context:
            payload['context'] = extra_context
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level.upper())
    root.addHandler(handler)
