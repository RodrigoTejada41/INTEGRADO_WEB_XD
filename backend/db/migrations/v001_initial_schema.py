from __future__ import annotations

from sqlalchemy import Engine

from backend.models import Base

VERSION = 1
NAME = "initial_schema"


def upgrade(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)


def downgrade(engine: Engine) -> None:
    Base.metadata.drop_all(bind=engine)

