from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from agent_local.orders.repository import StoredOrder


DEFAULT_RECEIPT_WIDTH = 32


@dataclass(frozen=True)
class LocalPrintJob:
    order_uuid: str
    job_path: Path
    status: str
    printer_name: str | None
    message: str | None = None


def _money(value: Decimal | None) -> str:
    if value is None:
        return "0.00"
    return f"{value.quantize(Decimal('0.01')):.2f}"


def _clean_text(value: object) -> str:
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


def _safe_filename_part(value: object) -> str:
    text = _clean_text(value)
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in text)
    return safe[:40].strip("_") or "sem_numero"


def _fit(value: object, width: int) -> str:
    text = _clean_text(value)
    if len(text) <= width:
        return text
    return text[: max(width - 1, 0)] + "."


def _line(left: object, right: object, width: int) -> str:
    left_text = _clean_text(left)
    right_text = _clean_text(right)
    available = width - len(right_text) - 1
    if available <= 0:
        return _fit(right_text, width)
    return f"{_fit(left_text, available):<{available}} {right_text}"


def _center(value: object, width: int) -> str:
    return _fit(value, width).center(width)


def _separator(width: int) -> str:
    return "-" * width


def render_thermal_receipt(order: StoredOrder, *, width: int = DEFAULT_RECEIPT_WIDTH) -> str:
    width = max(24, min(width, 48))
    table_label = f"Mesa {order.table_reference}" if order.table_reference else "Mesa nao informada"
    operator = order.operator_name or order.operator_code or "Nao informado"
    lines = [
        _center("PRE-CONTA", width),
        _center(f"COMANDA {order.command_number}", width),
        _separator(width),
        _line(table_label, order.status.upper(), width),
        _fit(f"Operador: {operator}", width),
        _separator(width),
    ]

    for item in order.items:
        quantity = _money(item.quantity).rstrip("0").rstrip(".")
        lines.append(_fit(f"{quantity}x {item.description}", width))
        if item.notes:
            lines.append(_fit(f"Obs: {item.notes}", width))
        lines.append(_line(f"Unit {_money(item.unit_price)}", _money(item.line_total), width))

    lines.extend([_separator(width), _line("TOTAL", _money(order.total_amount), width)])

    if order.payments:
        lines.extend([_separator(width), _center("PAGAMENTOS", width)])
        for payment in order.payments:
            lines.append(_line(payment.payment_method, _money(payment.amount), width))

    lines.extend([_separator(width), datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"), ""])
    return "\n".join(lines)


class LocalOrderPrinter:
    def __init__(self, *, jobs_dir: str | Path, printer_name: str | None = None, width: int = DEFAULT_RECEIPT_WIDTH):
        self.jobs_dir = Path(jobs_dir)
        self.printer_name = self._validate_printer_name(printer_name)
        self.width = width

    def create_job(self, order: StoredOrder) -> LocalPrintJob:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        content = render_thermal_receipt(order, width=self.width)
        created_at = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        command_number = _safe_filename_part(order.command_number)
        job_path = self.jobs_dir / f"order_{command_number}_{created_at}.txt"
        job_path.write_text(content, encoding="utf-8")

        if not self.printer_name:
            return LocalPrintJob(
                order_uuid=order.uuid,
                job_path=job_path,
                status="queued",
                printer_name=None,
                message="LOCAL_ORDER_PRINTER_NAME nao configurado.",
            )

        if os.name != "nt":
            return LocalPrintJob(
                order_uuid=order.uuid,
                job_path=job_path,
                status="queued",
                printer_name=self.printer_name,
                message="Envio automatico disponivel apenas no Windows.",
            )

        return self._send_to_windows_printer(order_uuid=order.uuid, job_path=job_path)

    def _send_to_windows_printer(self, *, order_uuid: str, job_path: Path) -> LocalPrintJob:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Content -LiteralPath $args[0] | Out-Printer -Name $args[1]",
            str(job_path),
            self.printer_name or "",
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
        except Exception as exc:
            return LocalPrintJob(
                order_uuid=order_uuid,
                job_path=job_path,
                status="queued",
                printer_name=self.printer_name,
                message=f"Falha ao enviar para impressora: {exc}",
            )

        if completed.returncode == 0:
            return LocalPrintJob(order_uuid=order_uuid, job_path=job_path, status="sent", printer_name=self.printer_name)

        message = (completed.stderr or completed.stdout or "Falha desconhecida no spool de impressao.").strip()
        return LocalPrintJob(
            order_uuid=order_uuid,
            job_path=job_path,
            status="queued",
            printer_name=self.printer_name,
            message=message[:300],
        )

    @staticmethod
    def _validate_printer_name(printer_name: str | None) -> str | None:
        if printer_name is None:
            return None
        cleaned = printer_name.strip()
        if not cleaned:
            return None
        if len(cleaned) > 120 or any(char in cleaned for char in "\r\n;&|<>"):
            raise ValueError("LOCAL_ORDER_PRINTER_NAME invalido.")
        return cleaned
