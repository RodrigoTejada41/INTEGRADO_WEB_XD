from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class XDPrintQueueJob:
    job_path: Path
    printer_id: int
    terminal_id: int
    copies: int = 1


class XDPrinterQueueWriter:
    def __init__(self, mariadb_url: str):
        self.engine = create_engine(mariadb_url, pool_pre_ping=True, future=True)
        self.session_factory = sessionmaker(bind=self.engine, class_=Session, autoflush=False)

    def enqueue_jobs(self, jobs: list[XDPrintQueueJob]) -> int:
        inserted = 0
        with self.session_factory() as session:
            for job in jobs:
                if not job.job_path.exists():
                    continue
                print_text = job.job_path.read_text(encoding="utf-8")
                result = session.execute(
                    text(
                        """
                        INSERT INTO printerorder (PrinterId, TerminalId, Copies, ToPrint, UserId)
                        VALUES (:printer_id, :terminal_id, :copies, 1, 0)
                        """
                    ),
                    {
                        "printer_id": job.printer_id,
                        "terminal_id": job.terminal_id,
                        "copies": max(int(job.copies or 1), 1),
                    },
                )
                printer_order_id = self._last_insert_id(session, result)
                session.execute(
                    text(
                        """
                        INSERT INTO printerqueue (PrinterOrderId, PrintText)
                        VALUES (:printer_order_id, :print_text)
                        """
                    ),
                    {"printer_order_id": printer_order_id, "print_text": print_text},
                )
                inserted += 1
            session.commit()
        return inserted

    def _last_insert_id(self, session: Session, result) -> int:
        if result.lastrowid:
            return int(result.lastrowid)
        dialect = session.get_bind().dialect.name
        statement = "SELECT last_insert_rowid()" if dialect == "sqlite" else "SELECT LAST_INSERT_ID()"
        return int(session.execute(text(statement)).scalar_one())
