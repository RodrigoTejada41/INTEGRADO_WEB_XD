from __future__ import annotations

import logging

from app.config.settings import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=settings.log_level.upper(),
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
